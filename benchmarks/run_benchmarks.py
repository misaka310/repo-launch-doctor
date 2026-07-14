"""Explicit network benchmark runner; normal tests and CI never invoke it."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
from repo_launch_doctor import __version__, scan_repository  # noqa: E402


def _metric(counts: dict[str, int]) -> dict[str, object]:
    positives, negatives = counts["positive_labels"], counts["negative_labels"]
    return {
        **counts,
        "precision": counts["TP"] / (counts["TP"] + counts["FP"]) if counts["TP"] + counts["FP"] else None,
        "recall": counts["TP"] / (counts["TP"] + counts["FN"]) if positives else None,
        "coverage_status": "sufficient" if positives and negatives else "no_positive_labels" if not positives else "no_negative_labels",
    }


def _run(command: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(command, 1, "", f"timed out after {timeout}s")


def _write(payload: dict[str, object]) -> None:
    output = Path(__file__).with_name("results")
    output.mkdir(exist_ok=True)
    (output / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Benchmark results", "", f"Generated: {payload['generated_at']}", f"Tool version: {payload['tool_version']}", f"Complete run: {payload['complete_run']}; targets={payload['targets']}; fetched={payload['fetch_succeeded']}; failed={payload['fetch_failed']}; complete scans={payload['scan_completed']}; incomplete scans={payload['scan_incomplete']}; eligible={payload['eligible_for_metrics']}", "", "| Check | + labels | - labels | TP | FP | FN | Precision | Recall | Coverage |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for check, row in payload["metrics"].items():
        lines.append(f"| `{check}` | {row['positive_labels']} | {row['negative_labels']} | {row['TP']} | {row['FP']} | {row['FN']} | {row['precision']} | {row['recall']} | {row['coverage_status']} |")
    for title, rows in (("Repository results", payload["results"]), ("False positives", payload["false_positives"]), ("False negatives", payload["false_negatives"]), ("Execution errors", payload["execution_errors"])):
        lines.extend(["", f"## {title}", *[f"- {row['repository']} @ `{row['commit']}`: {row.get('error') or row.get('findings') or 'none'}" for row in rows]])
    (output / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args(argv)
    manifest = json.loads((Path(__file__).with_name("manifest.json")).read_text(encoding="utf-8"))
    wanted = set(args.only)
    items = [item for item in manifest["repositories"] if not wanted or item["repository"] in wanted or item["repository"].rsplit("/", 1)[-1].removesuffix(".git") in wanted]
    metrics: dict[str, dict[str, int]] = defaultdict(lambda: {"positive_labels": 0, "negative_labels": 0, "TP": 0, "FP": 0, "FN": 0})
    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="repo-launch-doctor-bench-") as temporary:
        for item in items:
            destination = Path(temporary) / item["repository"].rsplit("/", 1)[-1].removesuffix(".git")
            init = _run(["git", "init", str(destination)], 30)
            remote = _run(["git", "-C", str(destination), "remote", "add", "origin", item["repository"]], 30) if init.returncode == 0 else init
            fetch = _run(["git", "-C", str(destination), "fetch", "--depth", "1", "origin", item["commit"]]) if remote.returncode == 0 else remote
            checkout = _run(["git", "-C", str(destination), "checkout", "--detach", item["commit"]], 180) if fetch.returncode == 0 else fetch
            fetched = checkout.returncode == 0
            findings: list[str] = []
            complete = False
            error = None if fetched else (checkout.stderr or checkout.stdout)[-1000:]
            if fetched:
                try:
                    report = scan_repository(destination)
                    findings, complete = [finding.check_id for finding in report.findings], report.metadata.get("scan_complete", False)
                    if not complete: error = "scan returned INCOMPLETE"
                except Exception as exc:  # benchmark isolation
                    error = f"scan exception: {type(exc).__name__}: {exc}"
            eligible = fetched and complete
            if eligible:
                for check, expected in item["checks"].items():
                    metrics[check]["positive_labels" if expected else "negative_labels"] += 1
                    actual = check in findings
                    if actual and expected: metrics[check]["TP"] += 1
                    elif actual: metrics[check]["FP"] += 1
                    elif expected: metrics[check]["FN"] += 1
            results.append({"repository": item["repository"], "commit": item["commit"], "project_type": item["project_type"], "expected": item["checks"], "findings": findings, "fetch_succeeded": fetched, "scan_complete": complete, "eligible_for_metrics": eligible, "error": error})
    payload: dict[str, object] = {"generated_at": datetime.now(timezone.utc).isoformat(), "tool_version": __version__, "manifest_schema_version": manifest["schema_version"], "targets": len(items), "fetch_succeeded": sum(row["fetch_succeeded"] for row in results), "fetch_failed": sum(not row["fetch_succeeded"] for row in results), "scan_completed": sum(row["scan_complete"] for row in results), "scan_incomplete": sum(row["fetch_succeeded"] and not row["scan_complete"] for row in results), "eligible_for_metrics": sum(row["eligible_for_metrics"] for row in results), "results": results, "metrics": {check: _metric(counts) for check, counts in metrics.items()}}
    payload["complete_run"] = payload["targets"] == len(manifest["repositories"]) and payload["eligible_for_metrics"] == payload["targets"]
    payload["false_positives"] = [row for row in results if row["eligible_for_metrics"] and any(check in row["findings"] and not expected for check, expected in row["expected"].items())]
    payload["false_negatives"] = [row for row in results if row["eligible_for_metrics"] and any(check not in row["findings"] and expected for check, expected in row["expected"].items())]
    payload["execution_errors"] = [row for row in results if not row["eligible_for_metrics"]]
    _write(payload)
    return 0 if payload["complete_run"] or args.allow_partial else 1


if __name__ == "__main__":
    raise SystemExit(main())
