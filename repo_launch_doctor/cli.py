from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .constants import PACKAGE_VERSION, SEVERITY_ORDER
from .history import scan_git_history
from .scanner import scan_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-launch-doctor",
        description="Check whether a repository is easy to start and safe to publish.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {PACKAGE_VERSION}",
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
    scan.add_argument(
        "--include-absolute-path",
        action="store_true",
        help="Include the absolute repository path in generated reports (off by default for safe sharing)",
    )

    history = subparsers.add_parser(
        "history-scan",
        help="Scan selected Git commits and commit messages for secret-like values",
    )
    history.add_argument("path", nargs="?", default=".", help="Repository path")
    selection = history.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--range",
        dest="revision_range",
        help="Git revision range, for example origin/main..HEAD",
    )
    selection.add_argument(
        "--all-history",
        action="store_true",
        help="Scan all commits reachable from local refs",
    )
    selection.add_argument(
        "--commits-file",
        help="UTF-8 text file containing one commit SHA per line",
    )
    history.add_argument(
        "--output",
        default="reports/repo-launch-doctor-history",
        help="Directory for history-report.json and history-report.md",
    )
    return parser


def _should_fail(severities: list[str], threshold: str) -> bool:
    if threshold == "none":
        return False
    threshold_rank = SEVERITY_ORDER[threshold.upper()]
    return any(SEVERITY_ORDER[severity] <= threshold_rank for severity in severities)


def _run_history_scan(args: argparse.Namespace) -> int:
    try:
        root = Path(args.path).expanduser().resolve()
        output = Path(args.output).expanduser()
        if not output.is_absolute():
            output = Path.cwd() / output
        commits = None
        if args.commits_file:
            commits = Path(args.commits_file).expanduser().read_text(encoding="utf-8").splitlines()
        report = scan_git_history(
            root,
            revision_range=args.revision_range,
            all_history=args.all_history,
            commits=commits,
            output_directory=output,
        )
    except (OSError, ValueError) as exc:
        print(f"Repo Launch Doctor history scan could not complete: {exc}", file=sys.stderr)
        return 2

    print(f"Repository: {root}")
    print(f"History verdict: {report.verdict}")
    print(f"Commits scanned: {report.commits_scanned}")
    print(f"Findings: {len(report.findings)}")
    print(f"Binary patches not content-scanned: {report.binary_patches_skipped}")
    print(f"Reports: {output.resolve()}")
    return 1 if report.findings else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "history-scan":
        return _run_history_scan(args)

    try:
        root = Path(args.path).expanduser().resolve()
        output = Path(args.output).expanduser()
        if not output.is_absolute():
            output = Path.cwd() / output
        report = scan_repository(
            root,
            output_directory=output,
            include_absolute_path=args.include_absolute_path,
        )
    except (OSError, ValueError) as exc:
        print(f"Repo Launch Doctor could not complete: {exc}", file=sys.stderr)
        return 2

    score = "N/A" if report.score is None else f"{report.score}/100"
    print(f"Repository: {root}")
    print(f"Verdict: {report.verdict}")
    print(f"Score: {score}")
    print(
        "Findings: "
        + ", ".join(f"{severity}={count}" for severity, count in report.counts.items())
    )
    print(f"Reports: {output.resolve()}")

    if not report.is_complete:
        print(
            "The scan was incomplete. Resolve the coverage problem before using this report for release decisions.",
            file=sys.stderr,
        )
        return 2

    severities = [finding.severity for finding in report.findings]
    return 1 if _should_fail(severities, args.fail_on) else 0
