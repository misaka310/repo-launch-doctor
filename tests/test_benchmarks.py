from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks import run_benchmarks as runner


BASE_ITEM = {
    "repository": "https://github.com/example/tool.git",
    "commit": "a" * 40,
    "project_type": "Python CLI",
    "checks": {"missing-start-entrypoint": False},
    "reason": "The pinned revision declares a CLI entry point.",
}


def make_item(index: int, *, owner: str | None = None, name: str | None = None) -> dict[str, object]:
    owner = owner or f"owner{index}"
    name = name or f"repo{index}"
    return {
        "repository": f"https://github.com/{owner}/{name}.git",
        "commit": f"{index + 1:040x}",
        "project_type": "Python library",
        "checks": {"missing-start-entrypoint": False},
        "reason": "The pinned revision is an importable library.",
    }


def make_result(
    item: dict[str, object],
    *,
    fetch: bool = True,
    checkout: bool = True,
    scan: bool = True,
    findings: list[str] | None = None,
    error: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "target_id": runner._target_id(item),
        "repository": item["repository"],
        "commit": item["commit"],
        "project_type": item["project_type"],
        "labels": item["checks"],
        "fetch_succeeded": fetch,
        "checkout_succeeded": checkout,
        "scan_complete": scan,
        "findings": findings or [],
        "execution_error": error,
        "verdict": "PASS" if scan else "INCOMPLETE",
    }


class BenchmarkRunnerTests(unittest.TestCase):
    def test_public_manifest_has_positive_and_negative_examples(self) -> None:
        manifest = json.loads(
            (Path(__file__).resolve().parents[1] / "benchmarks" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        labels: dict[str, set[bool]] = {}
        for item in manifest["repositories"]:
            for check, expected in item["checks"].items():
                labels.setdefault(check, set()).add(expected)

        self.assertEqual(20, len(manifest["repositories"]))
        self.assertEqual({False, True}, labels["missing-start-entrypoint"])
        self.assertEqual({False, True}, labels["readme-missing-verification"])
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.cache = self.root / ".benchmark-cache"
        self.results = self.root / "benchmarks" / "results"
        self.patchers = [
            patch.object(runner, "CACHE", self.cache),
            patch.object(runner, "RESULTS", self.results),
            patch.object(runner, "TARGETS", self.results / "targets"),
            patch.object(runner, "CACHE_TARGETS", self.cache / "results" / "targets"),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temporary.cleanup()

    def test_target_ids_include_owner_commit_and_do_not_collide(self) -> None:
        npm = make_item(1, owner="npm", name="cli")
        npm["commit"] = "b" * 40
        github = make_item(2, owner="cli", name="cli")
        github["commit"] = "c" * 40
        self.assertEqual(runner._target_id(npm), "npm--cli--bbbbbbbbbbbb")
        self.assertEqual(runner._target_id(github), "cli--cli--cccccccccccc")
        self.assertNotEqual(runner._target_id(npm), runner._target_id(github))

        later = dict(npm)
        later["commit"] = "d" * 40
        self.assertNotEqual(runner._target_id(npm), runner._target_id(later))

    def test_fresh_fetch_uses_init_shallow_fixed_sha_and_never_clone(self) -> None:
        commands: list[list[str]] = []
        item = dict(BASE_ITEM)

        def fake_run(command: list[str], timeout: int) -> tuple[int, str, str, bool]:
            commands.append(command)
            if "scan" in command:
                output = Path(command[command.index("--output") + 1])
                output.mkdir(parents=True, exist_ok=True)
                (output / "report.json").write_text(
                    json.dumps(
                        {
                            "verdict": "PASS",
                            "metadata": {"scan_complete": True},
                            "findings": [],
                        }
                    ),
                    encoding="utf-8",
                )
            if command[-2:] == ["rev-parse", "HEAD"]:
                return 0, str(item["commit"]) + "\n", "", False
            return 0, "", "", False

        with patch.object(runner, "_run", side_effect=fake_run):
            result = runner._run_target(item, force_repository=False)

        flattened = [part for command in commands for part in command]
        self.assertNotIn("clone", flattened)
        self.assertTrue(any("init" in command for command in commands))
        self.assertTrue(any(command[-4:-1] == ["remote", "add", "origin"] for command in commands))
        fetch = next(command for command in commands if "fetch" in command)
        self.assertIn("--depth=1", fetch)
        self.assertIn("--no-tags", fetch)
        self.assertEqual(fetch[-1], item["commit"])
        checkout = next(command for command in commands if "checkout" in command)
        self.assertEqual(checkout[-1], "FETCH_HEAD")
        self.assertTrue(result["fetch_succeeded"])
        self.assertTrue(result["checkout_succeeded"])
        self.assertTrue(result["scan_complete"])

    def test_existing_stale_repository_updates_remote_before_fetch(self) -> None:
        item = dict(BASE_ITEM)
        repository = self.cache / "repositories" / runner._target_id(item)
        (repository / ".git").mkdir(parents=True)
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout: int) -> tuple[int, str, str, bool]:
            commands.append(command)
            if command[-2:] == ["rev-parse", "--is-inside-work-tree"]:
                return 0, "true\n", "", False
            if command[-3:] == ["remote", "get-url", "origin"]:
                return 0, "https://github.com/other/repo.git\n", "", False
            if command[-2:] == ["rev-parse", "HEAD"]:
                return 0, str(item["commit"]) + "\n", "", False
            if "scan" in command:
                output = Path(command[command.index("--output") + 1])
                output.mkdir(parents=True, exist_ok=True)
                (output / "report.json").write_text(
                    json.dumps({"verdict": "PASS", "metadata": {"scan_complete": True}, "findings": []}),
                    encoding="utf-8",
                )
            return 0, "", "", False

        with patch.object(runner, "_run", side_effect=fake_run):
            runner._run_target(item, force_repository=False)

        self.assertTrue(any(command[-4:-1] == ["remote", "set-url", "origin"] for command in commands))
        self.assertTrue(any("fetch" in command for command in commands))

    def test_missing_git_directory_is_not_a_valid_repository_cache(self) -> None:
        item = dict(BASE_ITEM)
        repository = self.cache / "repositories" / runner._target_id(item)
        repository.mkdir(parents=True)
        with patch.object(runner, "_run") as mocked:
            self.assertFalse(runner._repository_cache_is_valid(item, repository))
        mocked.assert_not_called()

    def test_invalid_git_repository_is_not_reused(self) -> None:
        item = dict(BASE_ITEM)
        repository = self.cache / "repositories" / runner._target_id(item)
        (repository / ".git").mkdir(parents=True)
        with patch.object(runner, "_run", return_value=(1, "", "bad repository", False)):
            self.assertFalse(runner._repository_cache_is_valid(item, repository))

    def test_remote_url_mismatch_is_not_reused(self) -> None:
        item = dict(BASE_ITEM)
        repository = self.cache / "repositories" / runner._target_id(item)
        (repository / ".git").mkdir(parents=True)
        responses = [
            (0, "true\n", "", False),
            (0, "https://github.com/other/repo.git\n", "", False),
        ]
        with patch.object(runner, "_run", side_effect=responses):
            self.assertFalse(runner._repository_cache_is_valid(item, repository))

    def test_missing_fixed_sha_is_not_reused(self) -> None:
        item = dict(BASE_ITEM)
        repository = self.cache / "repositories" / runner._target_id(item)
        (repository / ".git").mkdir(parents=True)
        responses = [
            (0, "true\n", "", False),
            (0, str(item["repository"]) + "\n", "", False),
            (1, "", "missing commit", False),
        ]
        with patch.object(runner, "_run", side_effect=responses):
            self.assertFalse(runner._repository_cache_is_valid(item, repository))

    def test_head_mismatch_is_not_reused(self) -> None:
        item = dict(BASE_ITEM)
        repository = self.cache / "repositories" / runner._target_id(item)
        (repository / ".git").mkdir(parents=True)
        responses = [
            (0, "true\n", "", False),
            (0, str(item["repository"]) + "\n", "", False),
            (0, "", "", False),
            (0, "b" * 40 + "\n", "", False),
        ]
        with patch.object(runner, "_run", side_effect=responses):
            self.assertFalse(runner._repository_cache_is_valid(item, repository))

    def test_exact_fixed_sha_repository_cache_is_reused(self) -> None:
        item = dict(BASE_ITEM)
        repository = self.cache / "repositories" / runner._target_id(item)
        (repository / ".git").mkdir(parents=True)
        responses = [
            (0, "true\n", "", False),
            (0, str(item["repository"]) + "\n", "", False),
            (0, "", "", False),
            (0, str(item["commit"]) + "\n", "", False),
        ]
        with patch.object(runner, "_run", side_effect=responses):
            self.assertTrue(runner._repository_cache_is_valid(item, repository))

    def test_corrupt_target_json_is_not_a_successful_resume_cache(self) -> None:
        item = dict(BASE_ITEM)
        path = runner.CACHE_TARGETS / f"{runner._target_id(item)}.json"
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(runner._cached_target(item, force=False))

    def test_successful_resume_cache_requires_valid_repository_cache(self) -> None:
        item = dict(BASE_ITEM)
        path = runner.CACHE_TARGETS / f"{runner._target_id(item)}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(make_result(item)), encoding="utf-8")
        with patch.object(runner, "_repository_cache_is_valid", return_value=False):
            self.assertIsNone(runner._cached_target(item, force=False))
        with patch.object(runner, "_repository_cache_is_valid", return_value=True):
            self.assertIsNotNone(runner._cached_target(item, force=False))

    def test_resume_cache_is_invalidated_when_labels_change(self) -> None:
        original = dict(BASE_ITEM)
        path = runner.CACHE_TARGETS / f"{runner._target_id(original)}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(make_result(original)), encoding="utf-8")
        changed = dict(original)
        changed["checks"] = {"missing-start-entrypoint": False, "readme-missing-verification": True}

        with patch.object(runner, "_repository_cache_is_valid", return_value=True):
            self.assertIsNone(runner._cached_target(changed, force=False))

    def test_force_never_reuses_successful_target_result(self) -> None:
        item = dict(BASE_ITEM)
        path = runner.CACHE_TARGETS / f"{runner._target_id(item)}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(make_result(item)), encoding="utf-8")
        with patch.object(runner, "_repository_cache_is_valid", return_value=True):
            self.assertIsNone(runner._cached_target(item, force=True))

    def test_failed_or_incomplete_targets_never_create_false_negatives(self) -> None:
        positive = dict(BASE_ITEM)
        positive["checks"] = {"missing-start-entrypoint": True}
        rows = [
            make_result(positive, fetch=False, checkout=False, scan=False, error={"stage": "fetch"}),
            make_result(positive, fetch=True, checkout=False, scan=False, error={"stage": "checkout"}),
            make_result(positive, fetch=True, checkout=True, scan=False, error={"stage": "scan_timeout"}),
            make_result(positive, fetch=True, checkout=True, scan=False, error={"stage": "scan"}),
            make_result(positive, fetch=True, checkout=True, scan=False, error={"stage": "scan_incomplete"}),
        ]
        metric = runner._metrics(rows)["missing-start-entrypoint"]
        self.assertEqual(metric["positive_labels"], 0)
        self.assertEqual(metric["FN"], 0)
        self.assertEqual(metric["coverage_status"], "no_eligible_results")

    def test_only_fetched_checked_out_complete_scans_are_metric_eligible(self) -> None:
        positive = dict(BASE_ITEM)
        positive["checks"] = {"missing-start-entrypoint": True}
        eligible = make_result(positive, findings=["missing-start-entrypoint"])
        ineligible = make_result(positive, checkout=False, scan=False, error={"stage": "checkout"})
        metric = runner._metrics([eligible, ineligible])["missing-start-entrypoint"]
        self.assertEqual(metric["positive_labels"], 1)
        self.assertEqual(metric["TP"], 1)
        self.assertEqual(metric["FN"], 0)

    def test_zero_positive_labels_has_null_recall(self) -> None:
        metric = runner._metrics([make_result(dict(BASE_ITEM))])["missing-start-entrypoint"]
        self.assertEqual(metric["positive_labels"], 0)
        self.assertEqual(metric["negative_labels"], 1)
        self.assertIsNone(metric["recall"])
        self.assertEqual(metric["coverage_status"], "no_positive_labels")

    def test_zero_negative_labels_reports_no_negative_coverage(self) -> None:
        positive = dict(BASE_ITEM)
        positive["checks"] = {"missing-start-entrypoint": True}
        metric = runner._metrics([make_result(positive, findings=["missing-start-entrypoint"])])["missing-start-entrypoint"]
        self.assertEqual(metric["negative_labels"], 0)
        self.assertEqual(metric["coverage_status"], "no_negative_labels")

    def test_manifest_allows_same_repository_at_distinct_commits(self) -> None:
        first = make_item(1, owner="same", name="repo")
        first["commit"] = "a" * 40
        second = dict(first)
        second["commit"] = "b" * 40
        manifest = {"repositories": [first, second] + [make_item(index) for index in range(2, 20)]}
        errors = runner._validate_manifest(manifest)
        self.assertEqual([], errors)

    def test_manifest_rejects_duplicate_repository_commit_pair(self) -> None:
        first = make_item(1, owner="same", name="repo")
        second = dict(first)
        manifest = {
            "repositories": [first, second] + [make_item(index) for index in range(2, 20)]
        }
        errors = runner._validate_manifest(manifest)
        self.assertTrue(any("repository and commit" in error for error in errors), errors)

    def test_invalid_manifest_returns_exit_code_2(self) -> None:
        with patch.object(runner, "_load_manifest", return_value={"repositories": []}):
            self.assertEqual(runner.main([]), 2)

    def test_resume_skips_a_successful_target(self) -> None:
        item = dict(BASE_ITEM)
        manifest = {"repositories": [item] + [make_item(index) for index in range(1, 20)]}
        cached = make_result(item)
        with (
            patch.object(runner, "_load_manifest", return_value=manifest),
            patch.object(runner, "_cached_target", return_value=cached),
            patch.object(runner, "_run_target") as run_target,
        ):
            code = runner.main(["--resume", "--only", runner._target_id(item), "--allow-partial"])
        self.assertEqual(code, 0)
        run_target.assert_not_called()

    def test_force_reruns_a_successful_target(self) -> None:
        item = dict(BASE_ITEM)
        manifest = {"repositories": [item] + [make_item(index) for index in range(1, 20)]}
        with (
            patch.object(runner, "_load_manifest", return_value=manifest),
            patch.object(runner, "_cached_target", return_value=make_result(item)),
            patch.object(runner, "_run_target", return_value=make_result(item)) as run_target,
        ):
            code = runner.main(["--resume", "--force", "--only", runner._target_id(item), "--allow-partial"])
        self.assertEqual(code, 0)
        run_target.assert_called_once_with(item, force_repository=True)

    def test_partial_run_returns_1_by_default_and_0_only_when_allowed(self) -> None:
        item = dict(BASE_ITEM)
        manifest = {"repositories": [item] + [make_item(index) for index in range(1, 20)]}
        incomplete = make_result(item, scan=False, error={"stage": "scan_incomplete"})
        with (
            patch.object(runner, "_load_manifest", return_value=manifest),
            patch.object(runner, "_run_target", return_value=incomplete),
        ):
            self.assertEqual(runner.main(["--only", runner._target_id(item)]), 1)
            self.assertEqual(runner.main(["--only", runner._target_id(item), "--allow-partial"]), 0)

    def test_partial_run_does_not_create_or_replace_public_results(self) -> None:
        item = dict(BASE_ITEM)
        manifest = {"repositories": [item] + [make_item(index) for index in range(1, 20)]}
        self.results.mkdir(parents=True)
        sentinel = self.results / "latest.json"
        sentinel.write_text('{"published":"previous-complete-run"}\n', encoding="utf-8")
        incomplete = make_result(item, scan=False, error={"stage": "scan_timeout"})
        with (
            patch.object(runner, "_load_manifest", return_value=manifest),
            patch.object(runner, "_run_target", return_value=incomplete),
        ):
            runner.main(["--only", runner._target_id(item), "--allow-partial"])
        self.assertEqual(json.loads(sentinel.read_text(encoding="utf-8"))["published"], "previous-complete-run")
        self.assertFalse((self.results / "targets").exists())

    def test_complete_20_target_run_publishes_aggregate_and_unique_targets(self) -> None:
        items = [make_item(index) for index in range(20)]
        manifest = {"repositories": items}
        with (
            patch.object(runner, "_load_manifest", return_value=manifest),
            patch.object(runner, "_run_target", side_effect=[make_result(item) for item in items]),
        ):
            code = runner.main([])
        self.assertEqual(code, 0)
        payload = json.loads((self.results / "latest.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["targets"], 20)
        self.assertEqual(payload["fetch_succeeded"], 20)
        self.assertEqual(payload["fetch_failed"], 0)
        self.assertEqual(payload["checkout_succeeded"], 20)
        self.assertEqual(payload["checkout_failed"], 0)
        self.assertEqual(payload["scan_completed"], 20)
        self.assertEqual(payload["scan_incomplete"], 0)
        self.assertEqual(payload["eligible_for_metrics"], 20)
        self.assertEqual(payload["execution_errors"], 0)
        self.assertTrue(payload["complete_run"])
        self.assertFalse(payload["partial_result"])
        self.assertEqual(len(list((self.results / "targets").glob("*.json"))), 20)
        self.assertTrue((self.results / "latest.md").exists())

    def test_public_results_do_not_contain_local_or_cache_paths(self) -> None:
        items = [make_item(index) for index in range(20)]
        manifest = {"repositories": items}
        with (
            patch.object(runner, "_load_manifest", return_value=manifest),
            patch.object(runner, "_run_target", side_effect=[make_result(item) for item in items]),
        ):
            runner.main([])
        published = (self.results / "latest.json").read_text(encoding="utf-8")
        self.assertNotIn(str(self.root), published)
        self.assertNotIn(".benchmark-cache", published)
        self.assertNotIn("C:\\", published)

    def test_payload_counts_checkout_failures_and_execution_errors(self) -> None:
        items = [make_item(index) for index in range(20)]
        rows = [make_result(item) for item in items]
        rows[0] = make_result(
            items[0],
            fetch=True,
            checkout=False,
            scan=False,
            error={"stage": "checkout", "timed_out": False, "stderr": "failed"},
        )
        payload = runner._build_payload(items, rows)
        self.assertEqual(payload["fetch_succeeded"], 20)
        self.assertEqual(payload["checkout_succeeded"], 19)
        self.assertEqual(payload["checkout_failed"], 1)
        self.assertEqual(payload["scan_completed"], 19)
        self.assertEqual(payload["eligible_for_metrics"], 19)
        self.assertEqual(payload["execution_errors"], 1)
        self.assertFalse(payload["complete_run"])
        self.assertTrue(payload["partial_result"])


if __name__ == "__main__":
    unittest.main()
