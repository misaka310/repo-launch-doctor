"""Run the fixed-SHA corpus without making normal CI depend on the network."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).parents[1]
CACHE = ROOT / ".benchmark-cache"
RESULTS = Path(__file__).with_name("results")
TARGETS = RESULTS / "targets"
CACHE_TARGETS = CACHE / "results" / "targets"
FETCH_TIMEOUT, CHECKOUT_TIMEOUT, SCAN_TIMEOUT = 180, 60, 180
sys.path.insert(0, str(ROOT))
from repo_launch_doctor import __version__  # noqa: E402


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value


def _run(command: list[str], timeout: int) -> tuple[int, str, str, bool]:
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return done.returncode, done.stdout, done.stderr, False
    except subprocess.TimeoutExpired as exc:
        stdout = _text(exc.stdout)
        stderr = _text(exc.stderr)
        return 1, stdout, stderr + f"\ntimed out after {timeout}s", True


def _target_id(item: dict[str, Any]) -> str:
    path = urlparse(item["repository"]).path.strip("/")
    owner, name = path.split("/", 1)
    name = name.removesuffix(".git")
    raw = f"{owner}--{name}".lower()
    return re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-")


def _repository_name(item: dict[str, Any]) -> str:
    return urlparse(item["repository"]).path.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")


def _error(stage: str, stderr: str, timed_out: bool = False) -> dict[str, Any]:
    return {"stage": stage, "timed_out": timed_out, "stderr": stderr[-1200:]}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _load_manifest() -> dict[str, Any] | None:
    return _read_json(Path(__file__).with_name("manifest.json"))


def _validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entries = manifest.get("repositories")
    if not isinstance(entries, list) or len(entries) != 20:
        return ["manifest must contain exactly 20 repositories"]
    repositories: set[str] = set()
    target_ids: set[str] = set()
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            errors.append(f"repositories[{index}] is not an object")
            continue
        for key in ("repository", "commit", "project_type", "checks", "reason"):
            if key not in item:
                errors.append(f"repositories[{index}] missing {key}")
        repository = item.get("repository")
        if not isinstance(repository, str) or not repository.startswith("https://github.com/"):
            errors.append(f"repositories[{index}] has invalid repository")
        else:
            parts = urlparse(repository).path.strip("/").split("/")
            if len(parts) != 2 or not all(parts):
                errors.append(f"repositories[{index}] has invalid GitHub repository path")
            if repository in repositories:
                errors.append(f"repositories[{index}] duplicates repository")
            repositories.add(repository)
            try:
                target_id = _target_id(item)
            except (KeyError, ValueError):
                target_id = ""
            if target_id in target_ids:
                errors.append(f"repositories[{index}] duplicates target id {target_id}")
            target_ids.add(target_id)
        commit = item.get("commit")
        if (
            not isinstance(commit, str)
            or len(commit) != 40
            or any(char not in "0123456789abcdef" for char in commit)
        ):
            errors.append(f"repositories[{index}] has invalid commit SHA")
        checks = item.get("checks")
        if not isinstance(checks, dict) or not all(
            isinstance(key, str) and isinstance(value, bool) for key, value in checks.items()
        ):
            errors.append(f"repositories[{index}] has invalid check labels")
        if not isinstance(item.get("project_type"), str) or not item.get("project_type"):
            errors.append(f"repositories[{index}] has invalid project_type")
        if not isinstance(item.get("reason"), str) or not item.get("reason"):
            errors.append(f"repositories[{index}] has invalid reason")
    return errors


def _git_repository_is_valid(repository: Path) -> bool:
    if not (repository / ".git").exists():
        return False
    code, stdout, _, timed_out = _run(
        ["git", "-C", str(repository), "rev-parse", "--is-inside-work-tree"],
        CHECKOUT_TIMEOUT,
    )
    return not timed_out and code == 0 and stdout.strip() == "true"


def _repository_cache_is_valid(item: dict[str, Any], repository: Path) -> bool:
    if not _git_repository_is_valid(repository):
        return False
    code, stdout, _, timed_out = _run(
        ["git", "-C", str(repository), "remote", "get-url", "origin"],
        CHECKOUT_TIMEOUT,
    )
    if timed_out or code or stdout.strip() != item["repository"]:
        return False
    code, _, _, timed_out = _run(
        ["git", "-C", str(repository), "cat-file", "-e", f"{item['commit']}^{{commit}}"],
        CHECKOUT_TIMEOUT,
    )
    if timed_out or code:
        return False
    code, stdout, _, timed_out = _run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        CHECKOUT_TIMEOUT,
    )
    return not timed_out and code == 0 and stdout.strip() == item["commit"]


def _cached_target(item: dict[str, Any], force: bool) -> dict[str, Any] | None:
    if force:
        return None
    target_id = _target_id(item)
    existing = _read_json(CACHE_TARGETS / f"{target_id}.json")
    repository = CACHE / "repositories" / target_id
    if (
        existing
        and existing.get("target_id") == target_id
        and existing.get("repository") == item["repository"]
        and existing.get("commit") == item["commit"]
        and existing.get("fetch_succeeded") is True
        and existing.get("checkout_succeeded") is True
        and existing.get("scan_complete") is True
        and existing.get("execution_error") is None
        and _repository_cache_is_valid(item, repository)
    ):
        return existing
    return None


def _new_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_id": _target_id(item),
        "repository": item["repository"],
        "commit": item["commit"],
        "project_type": item["project_type"],
        "labels": item["checks"],
        "fetch_succeeded": False,
        "checkout_succeeded": False,
        "scan_complete": False,
        "findings": [],
        "execution_error": None,
    }


def _run_target(item: dict[str, Any], force_repository: bool = False) -> dict[str, Any]:
    target_id = _target_id(item)
    repository = CACHE / "repositories" / target_id
    scan_output = CACHE / "scans" / target_id
    result = _new_result(item)

    exact_cache = not force_repository and _repository_cache_is_valid(item, repository)
    if exact_cache:
        result["fetch_succeeded"] = True
        result["checkout_succeeded"] = True
    else:
        repository.parent.mkdir(parents=True, exist_ok=True)
        if not _git_repository_is_valid(repository):
            if repository.exists():
                shutil.rmtree(repository)
            code, _, stderr, timed_out = _run(
                ["git", "-c", "protocol.version=2", "init", str(repository)],
                CHECKOUT_TIMEOUT,
            )
            if code:
                result["execution_error"] = _error("init", stderr, timed_out)
                return result
            code, _, stderr, timed_out = _run(
                ["git", "-C", str(repository), "remote", "add", "origin", item["repository"]],
                CHECKOUT_TIMEOUT,
            )
            if code:
                result["execution_error"] = _error("remote", stderr, timed_out)
                return result
        else:
            code, _, stderr, timed_out = _run(
                ["git", "-C", str(repository), "remote", "set-url", "origin", item["repository"]],
                CHECKOUT_TIMEOUT,
            )
            if code:
                result["execution_error"] = _error("remote", stderr, timed_out)
                return result

        code, _, stderr, timed_out = _run(
            [
                "git",
                "-c",
                "protocol.version=2",
                "-C",
                str(repository),
                "fetch",
                "--depth=1",
                "--no-tags",
                "origin",
                item["commit"],
            ],
            FETCH_TIMEOUT,
        )
        if code:
            result["execution_error"] = _error("fetch", stderr, timed_out)
            return result
        result["fetch_succeeded"] = True

        code, _, stderr, timed_out = _run(
            ["git", "-C", str(repository), "checkout", "--detach", "--force", "FETCH_HEAD"],
            CHECKOUT_TIMEOUT,
        )
        if code:
            result["execution_error"] = _error("checkout", stderr, timed_out)
            return result
        code, stdout, stderr, timed_out = _run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            CHECKOUT_TIMEOUT,
        )
        if code or timed_out or stdout.strip() != item["commit"]:
            result["execution_error"] = _error(
                "checkout_verify",
                stderr or f"HEAD {stdout.strip()} did not match pinned SHA",
                timed_out,
            )
            return result
        result["checkout_succeeded"] = True

    if scan_output.exists():
        shutil.rmtree(scan_output)
    code, _, stderr, timed_out = _run(
        [
            sys.executable,
            "-m",
            "repo_launch_doctor",
            "scan",
            str(repository),
            "--output",
            str(scan_output),
            "--fail-on",
            "none",
        ],
        SCAN_TIMEOUT,
    )
    report = _read_json(scan_output / "report.json")
    if timed_out:
        result["execution_error"] = _error("scan_timeout", stderr, True)
        return result
    if code not in (0, 1, 2) or report is None:
        result["execution_error"] = _error("scan", stderr)
        return result
    result["findings"] = [
        finding.get("check_id")
        for finding in report.get("findings", [])
        if isinstance(finding, dict) and isinstance(finding.get("check_id"), str)
    ]
    result["scan_complete"] = (
        report.get("verdict") != "INCOMPLETE"
        and isinstance(report.get("metadata"), dict)
        and report["metadata"].get("scan_complete") is True
    )
    result["verdict"] = report.get("verdict")
    if not result["scan_complete"]:
        result["execution_error"] = _error("scan_incomplete", "report verdict was INCOMPLETE")
    return result


def _eligible(row: dict[str, Any]) -> bool:
    return bool(
        row.get("fetch_succeeded")
        and row.get("checkout_succeeded")
        and row.get("scan_complete")
        and row.get("execution_error") is None
    )


def _metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    labels = sorted(
        {
            check
            for row in rows
            for check in row.get("labels", {})
            if isinstance(check, str)
        }
    )
    counts: dict[str, dict[str, int]] = {
        check: {"positive_labels": 0, "negative_labels": 0, "TP": 0, "FP": 0, "FN": 0, "TN": 0}
        for check in labels
    }
    for row in rows:
        if not _eligible(row):
            continue
        observed = set(row.get("findings", []))
        for check, expected in row.get("labels", {}).items():
            bucket = counts[check]
            bucket["positive_labels" if expected else "negative_labels"] += 1
            bucket[
                "TP"
                if expected and check in observed
                else "FN"
                if expected
                else "FP"
                if check in observed
                else "TN"
            ] += 1
    output: dict[str, dict[str, Any]] = {}
    for check, value in counts.items():
        positives = value["positive_labels"]
        negatives = value["negative_labels"]
        denominator = value["TP"] + value["FP"]
        if positives and negatives:
            coverage = "sufficient"
        elif positives:
            coverage = "no_negative_labels"
        elif negatives:
            coverage = "no_positive_labels"
        else:
            coverage = "no_eligible_results"
        output[check] = {
            **value,
            "precision": value["TP"] / denominator if denominator else None,
            "recall": value["TP"] / positives if positives else None,
            "coverage_status": coverage,
        }
    return output


def _public_error(error: Any) -> dict[str, Any] | None:
    if not isinstance(error, dict):
        return None
    return {
        "stage": error.get("stage"),
        "timed_out": error.get("timed_out") is True,
    }


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_id": row.get("target_id"),
        "repository": row.get("repository"),
        "commit": row.get("commit"),
        "project_type": row.get("project_type"),
        "labels": row.get("labels", {}),
        "fetch_succeeded": row.get("fetch_succeeded") is True,
        "checkout_succeeded": row.get("checkout_succeeded") is True,
        "scan_complete": row.get("scan_complete") is True,
        "findings": row.get("findings", []),
        "execution_error": _public_error(row.get("execution_error")),
        "verdict": row.get("verdict"),
    }


def _build_payload(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    public_rows = [_public_row(row) for row in rows]
    fetch_succeeded = sum(row["fetch_succeeded"] for row in public_rows)
    checkout_succeeded = sum(row["checkout_succeeded"] for row in public_rows)
    scan_completed = sum(row["scan_complete"] for row in public_rows)
    eligible = sum(_eligible(row) for row in public_rows)
    error_details = [row for row in public_rows if row["execution_error"]]
    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool_version": __version__,
        "targets": len(items),
        "fetch_succeeded": fetch_succeeded,
        "fetch_failed": len(items) - fetch_succeeded,
        "checkout_succeeded": checkout_succeeded,
        "checkout_failed": len(items) - checkout_succeeded,
        "scan_completed": scan_completed,
        "scan_incomplete": len(items) - scan_completed,
        "eligible_for_metrics": eligible,
        "execution_errors": len(error_details),
        "execution_error_details": error_details,
        "results": public_rows,
    }
    payload["complete_run"] = (
        len(items) == 20
        and fetch_succeeded == 20
        and checkout_succeeded == 20
        and scan_completed == 20
        and eligible == 20
        and not error_details
    )
    payload["partial_result"] = not payload["complete_run"]
    payload["metrics"] = _metrics(public_rows)
    payload["false_positives"] = [
        row
        for row in public_rows
        if _eligible(row)
        and any(not expected and check in row["findings"] for check, expected in row["labels"].items())
    ]
    payload["false_negatives"] = [
        row
        for row in public_rows
        if _eligible(row)
        and any(expected and check not in row["findings"] for check, expected in row["labels"].items())
    ]
    return payload


def _format_metric(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Fixed-SHA benchmark results",
        "",
        f"Generated: {payload['generated_at']}",
        f"Tool version: {payload['tool_version']}",
        f"Complete run: `{str(payload['complete_run']).lower()}`; partial result: `{str(payload['partial_result']).lower()}`",
        "",
        "## Execution summary",
        "",
        f"- Targets: {payload['targets']}",
        f"- Fetch succeeded / failed: {payload['fetch_succeeded']} / {payload['fetch_failed']}",
        f"- Checkout succeeded / failed: {payload['checkout_succeeded']} / {payload['checkout_failed']}",
        f"- Scans complete / incomplete: {payload['scan_completed']} / {payload['scan_incomplete']}",
        f"- Eligible for metrics: {payload['eligible_for_metrics']}",
        f"- Execution errors: {payload['execution_errors']}",
        "",
        "## Metrics",
        "",
        "| Check | + | - | TP | FP | FN | TN | Precision | Recall | Coverage |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for check, row in payload["metrics"].items():
        lines.append(
            f"| `{check}` | {row['positive_labels']} | {row['negative_labels']} | "
            f"{row['TP']} | {row['FP']} | {row['FN']} | {row['TN']} | "
            f"{_format_metric(row['precision'])} | {_format_metric(row['recall'])} | "
            f"{row['coverage_status']} |"
        )
    lines.extend(["", "## Targets", ""])
    for row in payload["results"]:
        findings = ", ".join(row["findings"]) if row["findings"] else "none"
        lines.append(
            f"- `{row['target_id']}` `{row['commit']}` — {row['project_type']} — "
            f"verdict `{row.get('verdict')}` — findings: {findings}"
        )
    for heading, key in (
        ("False positives", "false_positives"),
        ("False negatives", "false_negatives"),
        ("Execution error details", "execution_error_details"),
    ):
        lines.extend(["", f"## {heading}", ""])
        rows = payload[key]
        if not rows:
            lines.append("- None")
        else:
            for row in rows:
                lines.append(
                    f"- `{row['target_id']}` `{row['commit']}`: "
                    f"{row.get('execution_error') or row.get('findings') or 'none'}"
                )
    return "\n".join(lines) + "\n"


def _select_items(items: list[dict[str, Any]], selectors: list[str]) -> list[dict[str, Any]] | None:
    if not selectors:
        return items
    selected: list[dict[str, Any]] = []
    for selector in selectors:
        matches = [
            item
            for item in items
            if selector in {_target_id(item), item["repository"], _repository_name(item)}
        ]
        if len(matches) != 1:
            return None
        if matches[0] not in selected:
            selected.append(matches[0])
    return selected


def _publish(payload: dict[str, Any]) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    if TARGETS.exists():
        shutil.rmtree(TARGETS)
    TARGETS.mkdir(parents=True)
    _write_json_atomic(RESULTS / "latest.json", payload)
    for row in payload["results"]:
        _write_json_atomic(TARGETS / f"{row['target_id']}.json", row)
    (RESULTS / "latest.md").write_text(_render_markdown(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args(argv)

    manifest = _load_manifest()
    if manifest is None:
        print("invalid manifest", file=sys.stderr)
        return 2
    errors = _validate_manifest(manifest)
    if errors:
        print("; ".join(errors), file=sys.stderr)
        return 2
    items = _select_items(manifest["repositories"], args.only)
    if items is None:
        print("one or more --only targets were not found or were ambiguous", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    for item in items:
        row = _cached_target(item, force=False) if args.resume and not args.force else None
        row = row or _run_target(item, force_repository=args.force)
        row["generated_at"] = datetime.now(timezone.utc).isoformat()
        _write_json_atomic(CACHE_TARGETS / f"{_target_id(item)}.json", row)
        rows.append(row)

    payload = _build_payload(items, rows)
    _write_json_atomic(CACHE / "results" / "aggregate.json", payload)
    if payload["complete_run"]:
        _publish(payload)
    return 0 if payload["complete_run"] or args.allow_partial else 1


if __name__ == "__main__":
    raise SystemExit(main())
