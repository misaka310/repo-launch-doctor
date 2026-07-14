"""Run the fixed-SHA corpus without making normal CI depend on the network."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
CACHE = ROOT / ".benchmark-cache"
RESULTS = Path(__file__).with_name("results")
TARGETS = RESULTS / "targets"
CACHE_TARGETS = CACHE / "results" / "targets"
FETCH_TIMEOUT, CHECKOUT_TIMEOUT, SCAN_TIMEOUT = 180, 60, 180
sys.path.insert(0, str(ROOT))
from repo_launch_doctor import __version__  # noqa: E402


def _run(command: list[str], timeout: int) -> tuple[int, str, str, bool]:
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return done.returncode, done.stdout, done.stderr, False
    except subprocess.TimeoutExpired as exc:
        return 1, exc.stdout or "", (exc.stderr or "") + f"\ntimed out after {timeout}s", True


def _slug(item: dict[str, Any]) -> str:
    return item["repository"].rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")


def _error(stage: str, stderr: str, timed_out: bool = False) -> dict[str, Any]:
    return {"stage": stage, "timed_out": timed_out, "stderr": stderr[-1200:]}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entries = manifest.get("repositories")
    if not isinstance(entries, list) or len(entries) != 20:
        return ["manifest must contain exactly 20 repositories"]
    seen: set[str] = set()
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            errors.append(f"repositories[{index}] is not an object")
            continue
        for key in ("repository", "commit", "project_type", "checks", "reason"):
            if key not in item: errors.append(f"repositories[{index}] missing {key}")
        if not isinstance(item.get("repository"), str) or not item["repository"].startswith("https://github.com/"):
            errors.append(f"repositories[{index}] has invalid repository")
        if not isinstance(item.get("commit"), str) or len(item["commit"]) != 40 or any(char not in "0123456789abcdef" for char in item["commit"]):
            errors.append(f"repositories[{index}] has invalid commit SHA")
        if item.get("repository") in seen: errors.append(f"repositories[{index}] duplicates repository")
        seen.add(item.get("repository", ""))
        if not isinstance(item.get("checks"), dict) or not all(isinstance(key, str) and isinstance(value, bool) for key, value in item.get("checks", {}).items()):
            errors.append(f"repositories[{index}] has invalid check labels")
    return errors


def _cached_target(item: dict[str, Any], force: bool) -> dict[str, Any] | None:
    path = CACHE_TARGETS / f"{_slug(item)}.json"
    existing = _read_json(path)
    if (
        not force
        and existing
        and existing.get("repository") == item["repository"]
        and existing.get("commit") == item["commit"]
        and existing.get("fetch_succeeded") is True
        and existing.get("scan_complete") is True
    ):
        return existing
    return None


def _run_target(item: dict[str, Any]) -> dict[str, Any]:
    slug = _slug(item)
    repository = CACHE / "repositories" / slug
    scan_output = CACHE / "scans" / slug
    result: dict[str, Any] = {"repository": item["repository"], "commit": item["commit"], "project_type": item["project_type"], "labels": item["checks"], "fetch_succeeded": False, "scan_complete": False, "findings": [], "execution_error": None}
    if not (repository / ".git").exists():
        if repository.exists(): shutil.rmtree(repository)
        code, _, stderr, timed_out = _run(["git", "-c", "protocol.version=2", "init", str(repository)], CHECKOUT_TIMEOUT)
        if code:
            result["execution_error"] = _error("init", stderr, timed_out); return result
        code, _, stderr, timed_out = _run(["git", "-C", str(repository), "remote", "add", "origin", item["repository"]], CHECKOUT_TIMEOUT)
        if code:
            result["execution_error"] = _error("remote", stderr, timed_out); return result
    else:
        _run(["git", "-C", str(repository), "remote", "set-url", "origin", item["repository"]], CHECKOUT_TIMEOUT)
    code, _, stderr, timed_out = _run(["git", "-c", "protocol.version=2", "-C", str(repository), "fetch", "--depth=1", "--no-tags", "origin", item["commit"]], FETCH_TIMEOUT)
    if code:
        result["execution_error"] = _error("fetch", stderr, timed_out); return result
    code, _, stderr, timed_out = _run(["git", "-C", str(repository), "checkout", "--detach", "--force", "FETCH_HEAD"], CHECKOUT_TIMEOUT)
    if code:
        result["execution_error"] = _error("checkout", stderr, timed_out); return result
    result["fetch_succeeded"] = True
    if scan_output.exists(): shutil.rmtree(scan_output)
    code, _, stderr, timed_out = _run([sys.executable, "-m", "repo_launch_doctor", "scan", str(repository), "--output", str(scan_output), "--fail-on", "none"], SCAN_TIMEOUT)
    report = _read_json(scan_output / "report.json")
    if timed_out:
        result["execution_error"] = _error("scan_timeout", stderr, True); return result
    if code not in (0, 1, 2) or report is None:
        result["execution_error"] = _error("scan", stderr); return result
    result["findings"] = [finding.get("check_id") for finding in report.get("findings", []) if isinstance(finding, dict) and isinstance(finding.get("check_id"), str)]
    result["scan_complete"] = report.get("verdict") != "INCOMPLETE" and report.get("metadata", {}).get("scan_complete") is True
    result["verdict"] = report.get("verdict")
    if not result["scan_complete"]: result["execution_error"] = _error("scan_incomplete", "report verdict was INCOMPLETE")
    return result


def _metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"positive_labels": 0, "negative_labels": 0, "TP": 0, "FP": 0, "FN": 0, "TN": 0})
    for row in rows:
        if not (row["fetch_succeeded"] and row["scan_complete"]): continue
        observed = set(row["findings"])
        for check, expected in row["labels"].items():
            bucket = counts[check]; bucket["positive_labels" if expected else "negative_labels"] += 1
            bucket["TP" if expected and check in observed else "FN" if expected else "FP" if check in observed else "TN"] += 1
    output: dict[str, dict[str, Any]] = {}
    for check, value in counts.items():
        positives, negatives = value["positive_labels"], value["negative_labels"]
        output[check] = {**value, "precision": value["TP"] / (value["TP"] + value["FP"]) if value["TP"] + value["FP"] else None, "recall": value["TP"] / positives if positives else None, "coverage_status": "sufficient" if positives and negatives else "no_positive_labels" if not positives and (positives or negatives) else "no_negative_labels" if positives else "no_eligible_results"}
    return dict(sorted(output.items()))


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Fixed-SHA benchmark results", "", f"Generated: {payload['generated_at']}", f"Tool version: {payload['tool_version']}", f"Complete run: `{payload['complete_run']}`; partial result: `{payload['partial_result']}`", f"Targets: {payload['targets']}; fetched: {payload['fetch_succeeded']}; fetch failed: {payload['fetch_failed']}; scans complete: {payload['scan_completed']}; scans incomplete: {payload['scan_incomplete']}; eligible: {payload['eligible_for_metrics']}", "", "| Check | + | - | TP | FP | FN | TN | Precision | Recall | Coverage |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for check, row in payload["metrics"].items(): lines.append(f"| `{check}` | {row['positive_labels']} | {row['negative_labels']} | {row['TP']} | {row['FP']} | {row['FN']} | {row['TN']} | {row['precision']} | {row['recall']} | {row['coverage_status']} |")
    for heading, rows in (("Targets", payload["results"]), ("False positives", payload["false_positives"]), ("False negatives", payload["false_negatives"]), ("Execution errors", payload["execution_errors"])):
        lines.extend(["", f"## {heading}"])
        lines.extend(f"- `{row['commit']}` {row['repository']}: {row.get('execution_error') or row.get('findings') or 'none'}" for row in rows)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args(argv)
    manifest = _read_json(Path(__file__).with_name("manifest.json"))
    if manifest is None:
        print("invalid manifest", file=sys.stderr); return 2
    errors = _validate_manifest(manifest)
    if errors:
        print("; ".join(errors), file=sys.stderr); return 2
    selected = set(args.only)
    items = [item for item in manifest["repositories"] if not selected or _slug(item) in selected or item["repository"] in selected]
    if selected and len(items) != len(selected): print("one or more --only targets were not found", file=sys.stderr); return 2
    rows = []
    for item in items:
        row = _cached_target(item, args.force) if args.resume else None
        row = row or _run_target(item)
        row["generated_at"] = datetime.now(timezone.utc).isoformat()
        _write_json_atomic(CACHE_TARGETS / f"{_slug(item)}.json", row)
        rows.append(row)
    eligible = sum(row["fetch_succeeded"] and row["scan_complete"] for row in rows)
    payload: dict[str, Any] = {"generated_at": datetime.now(timezone.utc).isoformat(), "tool_version": __version__, "targets": len(items), "fetch_succeeded": sum(row["fetch_succeeded"] for row in rows), "fetch_failed": sum(not row["fetch_succeeded"] for row in rows), "scan_completed": sum(row["scan_complete"] for row in rows), "scan_incomplete": sum(row["fetch_succeeded"] and not row["scan_complete"] for row in rows), "eligible_for_metrics": eligible, "results": rows}
    payload["complete_run"] = len(items) == 20 and eligible == 20
    payload["partial_result"] = not payload["complete_run"]
    payload["metrics"] = _metrics(rows)
    payload["false_positives"] = [row for row in rows if row["fetch_succeeded"] and row["scan_complete"] and any(not expected and check in row["findings"] for check, expected in row["labels"].items())]
    payload["false_negatives"] = [row for row in rows if row["fetch_succeeded"] and row["scan_complete"] and any(expected and check not in row["findings"] for check, expected in row["labels"].items())]
    payload["execution_errors"] = [row for row in rows if row["execution_error"]]
    _write_json_atomic(CACHE / "results" / "aggregate.json", payload)
    if payload["complete_run"]:
        _write_json_atomic(RESULTS / "latest.json", payload)
        TARGETS.mkdir(parents=True, exist_ok=True)
        for row in rows:
            shutil.copyfile(CACHE_TARGETS / f"{_slug(row)}.json", TARGETS / f"{_slug(row)}.json")
        (RESULTS / "latest.md").write_text(_render_markdown(payload), encoding="utf-8")
    return 0 if payload["complete_run"] or args.allow_partial else 1


if __name__ == "__main__": raise SystemExit(main())
