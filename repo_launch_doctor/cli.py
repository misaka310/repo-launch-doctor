from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .models import SEVERITY_ORDER
from .scanner import scan_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-launch-doctor",
        description="Check whether a repository is easy to start and safe to publish.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="Scan one local repository")
    scan.add_argument("path", nargs="?", default=".", help="Repository path")
    scan.add_argument(
        "--output",
        default="reports/repo-launch-doctor",
        help="Directory for report.json, report.md, and report.html",
    )
    scan.add_argument(
        "--fail-on",
        choices=("none", "blocker", "high", "medium"),
        default="blocker",
        help="Return exit code 1 when this severity or worse is present",
    )
    return parser


def _should_fail(severities: list[str], threshold: str) -> bool:
    if threshold == "none":
        return False
    threshold_rank = SEVERITY_ORDER[threshold.upper()]
    return any(SEVERITY_ORDER[severity] <= threshold_rank for severity in severities)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        root = Path(args.path).expanduser().resolve()
        output = Path(args.output).expanduser()
        if not output.is_absolute():
            output = Path.cwd() / output
        report = scan_repository(root, output_directory=output)
    except (OSError, ValueError) as exc:
        print(f"Repo Launch Doctor could not complete: {exc}", file=sys.stderr)
        return 2

    print(f"Repository: {report.root}")
    print(f"Score: {report.score}/100")
    print(
        "Findings: "
        + ", ".join(f"{severity}={count}" for severity, count in report.counts.items())
    )
    print(f"Reports: {output.resolve()}")

    severities = [finding.severity for finding in report.findings]
    return 1 if _should_fail(severities, args.fail_on) else 0
