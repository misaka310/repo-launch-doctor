"""Explicit, networked benchmark runner; intentionally not used by unit tests or CI."""
from __future__ import annotations

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


def main() -> int:
    manifest = json.loads((Path(__file__).with_name("manifest.json")).read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    metrics: dict[str, dict[str, int]] = defaultdict(lambda: {"TP": 0, "FP": 0, "FN": 0})
    with tempfile.TemporaryDirectory(prefix="repo-launch-doctor-bench-") as temporary:
        temp = Path(temporary)
        for item in manifest["repositories"]:
            name = item["repository"].rsplit("/", 1)[-1].removesuffix(".git")
            destination = temp / name
            clone = subprocess.run(["git", "init", str(destination)], capture_output=True, text=True)
            if clone.returncode == 0:
                remote = subprocess.run(["git", "-C", str(destination), "remote", "add", "origin", item["repository"]], capture_output=True, text=True)
                try:
                    fetched = subprocess.run(["git", "-C", str(destination), "fetch", "--depth", "1", "origin", item["commit"]], capture_output=True, text=True, timeout=180)
                except subprocess.TimeoutExpired as exc:
                    fetched = subprocess.CompletedProcess(exc.cmd, 1, "", "fetch timed out after 180 seconds")
                checkout = remote.returncode == 0 and fetched.returncode == 0 and subprocess.run(["git", "-C", str(destination), "checkout", "--detach", item["commit"]], capture_output=True, text=True).returncode == 0
                error = (remote.stderr + fetched.stderr)[-1000:] if not checkout else None
            else:
                checkout, error = False, clone.stderr[-1000:]
            observed: list[str] = []
            if checkout:
                report = scan_repository(destination)
                observed = [finding.check_id for finding in report.findings]
                scan_complete = report.metadata.get("scan_complete", False)
                verdict = report.verdict
            else:
                scan_complete, verdict = False, None
            for check_id, expected in item["checks"].items():
                actual = check_id in observed
                if actual and expected:
                    metrics[check_id]["TP"] += 1
                elif actual:
                    metrics[check_id]["FP"] += 1
                elif expected:
                    metrics[check_id]["FN"] += 1
            results.append({"repository": item["repository"], "commit": item["commit"], "project_type": item["project_type"], "expected": item["checks"], "findings": observed, "fetch_succeeded": checkout, "scan_complete": scan_complete, "verdict": verdict, "error": error})
    summary = {check: {**counts, "precision": counts["TP"] / (counts["TP"] + counts["FP"]) if counts["TP"] + counts["FP"] else None, "recall": counts["TP"] / (counts["TP"] + counts["FN"]) if counts["TP"] + counts["FN"] else None} for check, counts in metrics.items()}
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "tool_version": __version__, "manifest_schema_version": manifest["schema_version"], "targets": len(manifest["repositories"]), "fetch_succeeded": sum(row["fetch_succeeded"] for row in results), "scan_completed": sum(row["scan_complete"] for row in results), "scan_incomplete": sum(row["fetch_succeeded"] and not row["scan_complete"] for row in results), "results": results, "metrics": summary, "false_positives": [row for row in results if row["fetch_succeeded"] and any(check in row["findings"] and not expected for check, expected in row["expected"].items())], "false_negatives": [row for row in results if row["fetch_succeeded"] and any(check not in row["findings"] and expected for check, expected in row["expected"].items())], "execution_errors": [row for row in results if not row["fetch_succeeded"] or not row["scan_complete"]]}
    output = Path(__file__).with_name("results")
    output.mkdir(exist_ok=True)
    (output / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Benchmark results", "", f"Generated: {payload['generated_at']}", f"Tool version: {__version__}", f"Targets: {payload['targets']}; fetched: {payload['fetch_succeeded']}; scans complete: {payload['scan_completed']}; scans incomplete: {payload['scan_incomplete']}", "", "| Check | TP | FP | FN | Precision | Recall |", "|---|---:|---:|---:|---:|---:|"]
    for check, row in summary.items(): lines.append(f"| `{check}` | {row['TP']} | {row['FP']} | {row['FN']} | {row['precision']} | {row['recall']} |")
    lines.extend(["", "## Repository results", ""])
    lines.extend(f"- `{row['commit']}` {row['repository']}: fetch={row['fetch_succeeded']}, complete={row['scan_complete']}, findings={', '.join(row['findings']) or 'none'}, error={row['error'] or 'none'}" for row in results)
    lines.extend(["", "## False positives", *[f"- {row['repository']} @ `{row['commit']}`" for row in payload["false_positives"]], "", "## False negatives", *[f"- {row['repository']} @ `{row['commit']}`" for row in payload["false_negatives"]], "", "## Execution errors", *[f"- {row['repository']} @ `{row['commit']}`: {row['error'] or 'incomplete scan'}" for row in payload["execution_errors"]]])
    (output / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
