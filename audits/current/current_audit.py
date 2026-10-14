"""Run a current-repository audit with labels assigned only after scanning.

Workflow:
1. ``select`` chooses repositories without using Repo Launch Doctor output.
2. ``scan`` scans the selected HEAD commits and stores raw results in an ignored cache.
3. ``packet`` creates an ignored review packet from the completed scans.
4. A reviewer writes ``manual-review.json``.
5. ``publish`` compares the completed scans with the later manual review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = Path(__file__).resolve().parent
SELECTION_PATH = AUDIT_DIR / "selection.json"
REVIEW_PATH = AUDIT_DIR / "manual-review.json"
RESULTS_DIR = AUDIT_DIR / "results"
CACHE = ROOT / ".current-audit-cache"
RAW_PATH = CACHE / "raw-scan-results.json"
PACKET_PATH = CACHE / "review-packet.md"
TARGET_COUNT = 30
PER_LANGUAGE = 5
LANGUAGES = ("Python", "JavaScript", "TypeScript", "Go", "C#", "Java")
SELECTION_SEED = "repo-launch-doctor-current-audit-2026-07-v1"
CHECKS = ("missing-start-entrypoint", "readme-missing-verification")
FETCH_TIMEOUT = 180
SCAN_TIMEOUT = 180

sys.path.insert(0, str(ROOT))
from benchmarks import run_benchmarks as benchmark  # noqa: E402
from repo_launch_doctor import __version__  # noqa: E402

benchmark.CACHE = CACHE
benchmark.CACHE_TARGETS = CACHE / "results" / "targets"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _run(command: list[str], timeout: int) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return 1, stdout, stderr + f"\ntimed out after {timeout}s"


def _github_search(language: str) -> list[dict[str, Any]]:
    query = (
        f"language:{language} fork:false archived:false "
        "stars:2..100 size:50..5000 pushed:>=2026-01-01"
    )
    url = (
        "https://api.github.com/search/repositories?q="
        + quote(query)
        + "&sort=updated&order=desc&per_page=100"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-launch-doctor-current-audit",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        remaining = exc.headers.get("X-RateLimit-Remaining")
        reset = exc.headers.get("X-RateLimit-Reset")
        raise RuntimeError(
            f"GitHub search failed for {language}: HTTP {exc.code}; "
            f"remaining={remaining}; reset={reset}"
        ) from exc
    items = payload.get("items")
    if not isinstance(items, list):
        raise RuntimeError(f"GitHub search returned no item list for {language}")
    return [item for item in items if isinstance(item, dict)]


def _candidate_key(full_name: str) -> str:
    return hashlib.sha256(f"{SELECTION_SEED}:{full_name.lower()}".encode()).hexdigest()


def _resolve_head(repository: str, branch: str) -> str | None:
    code, stdout, _ = _run(
        ["git", "ls-remote", "--heads", repository, f"refs/heads/{branch}"],
        FETCH_TIMEOUT,
    )
    if code:
        return None
    first = stdout.strip().splitlines()
    if not first:
        return None
    sha = first[0].split(maxsplit=1)[0].lower()
    return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else None


def select_repositories(force: bool = False) -> dict[str, Any]:
    if SELECTION_PATH.exists() and not force:
        raise RuntimeError(f"selection already exists: {SELECTION_PATH}")
    if RAW_PATH.exists() and not force:
        raise RuntimeError("raw scan results already exist; refusing outcome-dependent reselection")

    selected: list[dict[str, Any]] = []
    selected_names: set[str] = set()
    query_details: list[dict[str, Any]] = []
    for language in LANGUAGES:
        items = _github_search(language)
        candidates = sorted(items, key=lambda item: _candidate_key(str(item.get("full_name", ""))))
        accepted = 0
        rejected = 0
        for item in candidates:
            full_name = item.get("full_name")
            default_branch = item.get("default_branch")
            clone_url = item.get("clone_url")
            if (
                not isinstance(full_name, str)
                or not isinstance(default_branch, str)
                or not isinstance(clone_url, str)
                or full_name.lower() in selected_names
                or item.get("fork") is True
                or item.get("archived") is True
                or item.get("disabled") is True
            ):
                rejected += 1
                continue
            head_sha = _resolve_head(clone_url, default_branch)
            if head_sha is None:
                rejected += 1
                continue
            selected.append(
                {
                    "repository": clone_url,
                    "full_name": full_name,
                    "language_bucket": language,
                    "reported_primary_language": item.get("language"),
                    "default_branch": default_branch,
                    "head_sha": head_sha,
                    "stars": item.get("stargazers_count"),
                    "size_kb": item.get("size"),
                    "pushed_at": item.get("pushed_at"),
                    "updated_at": item.get("updated_at"),
                    "description": item.get("description"),
                }
            )
            selected_names.add(full_name.lower())
            accepted += 1
            if accepted == PER_LANGUAGE:
                break
        query_details.append(
            {
                "language": language,
                "returned": len(items),
                "accepted": accepted,
                "rejected_before_completion": rejected,
            }
        )
        if accepted != PER_LANGUAGE:
            raise RuntimeError(f"could not select {PER_LANGUAGE} repositories for {language}")

    payload = {
        "schema_version": 1,
        "selected_at": _utc_now(),
        "selection_completed_before_scan": True,
        "selection_policy": {
            "description": (
                "Six language buckets, five repositories per bucket. Candidates came from the first "
                "100 GitHub Search results sorted by recently updated, then were deterministically "
                "reordered by a declared seed. Selection did not use Doctor findings."
            ),
            "languages": list(LANGUAGES),
            "per_language": PER_LANGUAGE,
            "seed": SELECTION_SEED,
            "github_query_constraints": {
                "fork": False,
                "archived": False,
                "stars": "2..100",
                "size_kb": "50..5000",
                "pushed_since": "2026-01-01",
                "sort": "updated desc",
                "search_page_size": 100,
            },
            "limitations": (
                "This is a stratified current snapshot of small recently pushed repositories, not a "
                "statistically representative sample of all GitHub repositories."
            ),
            "queries": query_details,
        },
        "repositories": selected,
    }
    errors = validate_selection(payload)
    if errors:
        raise RuntimeError("; ".join(errors))
    _write_json_atomic(SELECTION_PATH, payload)
    return payload


def validate_selection(selection: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    repositories = selection.get("repositories")
    if not isinstance(repositories, list) or len(repositories) != TARGET_COUNT:
        return [f"selection must contain exactly {TARGET_COUNT} repositories"]
    names: set[str] = set()
    commits: set[tuple[str, str]] = set()
    buckets: dict[str, int] = {language: 0 for language in LANGUAGES}
    for index, item in enumerate(repositories):
        if not isinstance(item, dict):
            errors.append(f"repositories[{index}] is not an object")
            continue
        for key in ("repository", "full_name", "language_bucket", "default_branch", "head_sha"):
            if not isinstance(item.get(key), str) or not item.get(key):
                errors.append(f"repositories[{index}] has invalid {key}")
        repository = item.get("repository")
        full_name = item.get("full_name")
        sha = item.get("head_sha")
        if isinstance(repository, str) and not repository.startswith("https://github.com/"):
            errors.append(f"repositories[{index}] is not a GitHub repository")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            errors.append(f"repositories[{index}] has invalid head_sha")
        if isinstance(full_name, str):
            lowered = full_name.lower()
            if lowered in names:
                errors.append(f"repositories[{index}] duplicates full_name")
            names.add(lowered)
        if isinstance(repository, str) and isinstance(sha, str):
            key = (repository, sha)
            if key in commits:
                errors.append(f"repositories[{index}] duplicates repository and commit")
            commits.add(key)
        bucket = item.get("language_bucket")
        if bucket not in buckets:
            errors.append(f"repositories[{index}] has unknown language bucket")
        else:
            buckets[bucket] += 1
    for language, count in buckets.items():
        if count != PER_LANGUAGE:
            errors.append(f"language bucket {language} has {count}, expected {PER_LANGUAGE}")
    return errors


def _benchmark_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "repository": item["repository"],
        "commit": item["head_sha"],
        "project_type": "unreviewed current snapshot",
        "checks": {},
        "reason": "Selected before scanning; labels are assigned only after all scans complete.",
    }


def _report_for(item: dict[str, Any]) -> dict[str, Any] | None:
    target_id = benchmark._target_id(_benchmark_item(item))
    path = CACHE / "scans" / target_id / "report.json"
    try:
        value = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None
    return value


def _eligible_audit_row(row: dict[str, Any]) -> bool:
    return bool(
        row.get("fetch_succeeded") is True
        and row.get("checkout_succeeded") is True
        and row.get("scan_complete") is True
        and row.get("execution_error") is None
    )


def _raw_payload(
    selection: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    all_targets_attempted: bool,
) -> dict[str, Any]:
    eligible = sum(_eligible_audit_row(row) for row in rows)
    excluded = len(rows) - eligible
    return {
        "schema_version": 1,
        "selected_at": selection["selected_at"],
        "scan_completed_at": _utc_now() if all_targets_attempted else None,
        "last_updated_at": _utc_now(),
        "tool_version": __version__,
        "targets": len(selection["repositories"]),
        "processed_targets": len(rows),
        "eligible_targets": eligible,
        "excluded_targets": excluded,
        "all_targets_attempted": all_targets_attempted,
        "complete_run": all_targets_attempted and excluded == 0,
        "selection_policy": selection["selection_policy"],
        "results": rows,
    }


def scan_selection(force: bool = False, resume: bool = False) -> dict[str, Any]:
    selection = _read_json(SELECTION_PATH)
    errors = validate_selection(selection)
    if errors:
        raise RuntimeError("; ".join(errors))
    if RAW_PATH.exists() and not force and not resume:
        raise RuntimeError(f"raw scan results already exist: {RAW_PATH}")

    previous_rows: dict[tuple[str, str], dict[str, Any]] = {}
    if resume and RAW_PATH.exists() and not force:
        previous = _read_json(RAW_PATH)
        previous_rows = {
            (row["repository"], row["commit"]): row
            for row in previous.get("results", [])
            if isinstance(row, dict) and _eligible_audit_row(row)
        }

    rows: list[dict[str, Any]] = []
    for selected in selection["repositories"]:
        item = _benchmark_item(selected)
        key = (item["repository"], item["commit"])
        row = previous_rows.get(key)
        if row is None:
            row = benchmark._cached_target(item, force=False) if resume and not force else None
            row = row or benchmark._run_target(item, force_repository=force)
        report = _report_for(selected)
        metadata = report.get("metadata", {}) if isinstance(report, dict) else {}
        findings = report.get("findings", []) if isinstance(report, dict) else []
        row.update(
            {
                "full_name": selected["full_name"],
                "language_bucket": selected["language_bucket"],
                "default_branch": selected["default_branch"],
                "selected_head_sha": selected["head_sha"],
                "detected_project_type": metadata.get("project_type") if isinstance(metadata, dict) else None,
                "start_commands": metadata.get("start_commands", []) if isinstance(metadata, dict) else [],
                "verification_commands": (
                    metadata.get("verification_commands", []) if isinstance(metadata, dict) else []
                ),
                "finding_details": [
                    {
                        "check_id": finding.get("check_id"),
                        "severity": finding.get("severity"),
                        "title": finding.get("title"),
                        "path": finding.get("path"),
                    }
                    for finding in findings
                    if isinstance(finding, dict)
                ],
            }
        )
        rows.append(row)
        benchmark._write_json_atomic(
            benchmark.CACHE_TARGETS / f"{benchmark._target_id(item)}.json",
            row,
        )
        _write_json_atomic(
            RAW_PATH,
            _raw_payload(selection, rows, all_targets_attempted=False),
        )

    payload = _raw_payload(
        selection,
        rows,
        all_targets_attempted=len(rows) == TARGET_COUNT,
    )
    _write_json_atomic(RAW_PATH, payload)
    if not payload["all_targets_attempted"]:
        raise RuntimeError("not all selected targets were attempted")
    return payload


def _safe_read(path: Path, max_bytes: int = 180_000) -> str:
    try:
        raw = path.read_bytes()[:max_bytes]
        if b"\x00" in raw:
            return ""
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _line_excerpt(text: str, max_lines: int = 140) -> str:
    lines = text.splitlines()
    keywords = re.compile(
        r"(?i)(^#{1,4}\s|install|setup|usage|quickstart|getting started|run|start|serve|launch|"
        r"test|testing|verify|verification|pytest|unittest|npm |pnpm |yarn |docker|make )"
    )
    selected: set[int] = set(range(min(45, len(lines))))
    for index, line in enumerate(lines):
        if keywords.search(line):
            selected.update(range(max(0, index - 2), min(len(lines), index + 3)))
    ordered = sorted(selected)[:max_lines]
    return "\n".join(f"{index + 1:>4}: {lines[index]}" for index in ordered)


def _evidence_files(repository: Path) -> list[Path]:
    preferred = [
        "README.md",
        "README.rst",
        "README.txt",
        "README",
        "package.json",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        "Makefile",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    ]
    paths = [repository / name for name in preferred if (repository / name).is_file()]
    for pattern in ("*.bat", "*.cmd", "*.ps1", "*.sh", "*.sln"):
        for path in sorted(repository.glob(pattern), key=lambda value: value.name.lower()):
            if path not in paths:
                paths.append(path)
    return paths[:20]


def build_review_packet() -> Path:
    selection = _read_json(SELECTION_PATH)
    raw = _read_json(RAW_PATH)
    if not raw.get("all_targets_attempted"):
        raise RuntimeError("review packet requires every selected target to be attempted")
    rows = {row["repository"]: row for row in raw["results"]}
    lines = [
        "# Current audit review packet",
        "",
        f"Selected: {selection['selected_at']}",
        f"All attempts completed: {raw['scan_completed_at']}",
        f"Eligible for review: {raw['eligible_targets']}; excluded: {raw['excluded_targets']}",
        "",
        "Labels must be assigned only after reviewing these completed scan results and source evidence.",
        "Excluded targets are documented but are not manually labeled or included in metrics.",
        "",
    ]
    for index, selected in enumerate(selection["repositories"], start=1):
        item = _benchmark_item(selected)
        target_id = benchmark._target_id(item)
        repository = CACHE / "repositories" / target_id
        row = rows[selected["repository"]]
        lines.extend(
            [
                f"## {index}. {selected['full_name']}",
                "",
                f"- Commit: `{selected['head_sha']}`",
                f"- Bucket: {selected['language_bucket']}",
            ]
        )
        if not _eligible_audit_row(row):
            lines.extend(
                [
                    "- Review status: excluded",
                    f"- Execution error: `{row.get('execution_error')}`",
                    "",
                ]
            )
            continue
        root_files = sorted(path.name for path in repository.iterdir() if path.name != ".git")
        lines.extend(
            [
                "- Review status: eligible",
                f"- Doctor project type: `{row.get('detected_project_type')}`",
                f"- Doctor start commands: `{row.get('start_commands', [])}`",
                f"- Doctor verification commands: `{row.get('verification_commands', [])}`",
                f"- Doctor findings: `{row.get('findings', [])}`",
                f"- Root files: `{root_files}`",
                "",
            ]
        )
        for path in _evidence_files(repository):
            text = _safe_read(path)
            if not text:
                continue
            lines.extend(
                [
                    f"### `{path.name}`",
                    "",
                    "```text",
                    _line_excerpt(text),
                    "```",
                    "",
                ]
            )
    PACKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    PACKET_PATH.write_text("\n".join(lines), encoding="utf-8")
    return PACKET_PATH


def validate_review(raw: dict[str, Any], review: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not raw.get("all_targets_attempted"):
        errors.append("every selected target must be attempted before manual review")
    try:
        if _parse_time(review["reviewed_at"]) <= _parse_time(raw["scan_completed_at"]):
            errors.append("manual review must be dated after all scan attempts completed")
    except (KeyError, TypeError, ValueError):
        errors.append("manual review has invalid reviewed_at")
    eligible_rows = [row for row in raw.get("results", []) if _eligible_audit_row(row)]
    reviews = review.get("reviews")
    if not isinstance(reviews, list) or len(reviews) != len(eligible_rows):
        return errors + [
            f"manual review must contain exactly {len(eligible_rows)} eligible entries"
        ]
    raw_keys = {(row["repository"], row["commit"]) for row in eligible_rows}
    review_keys: set[tuple[str, str]] = set()
    for index, item in enumerate(reviews):
        if not isinstance(item, dict):
            errors.append(f"reviews[{index}] is not an object")
            continue
        key = (item.get("repository"), item.get("commit"))
        if key in review_keys:
            errors.append(f"reviews[{index}] duplicates repository and commit")
        review_keys.add(key)
        labels = item.get("labels")
        rationale = item.get("rationale")
        if not isinstance(labels, dict) or set(labels) != set(CHECKS):
            errors.append(f"reviews[{index}] must label exactly {CHECKS}")
        elif not all(isinstance(labels[check], bool) for check in CHECKS):
            errors.append(f"reviews[{index}] has non-boolean labels")
        if not isinstance(rationale, dict) or set(rationale) != set(CHECKS):
            errors.append(f"reviews[{index}] must explain exactly {CHECKS}")
        elif not all(isinstance(rationale[check], str) and rationale[check].strip() for check in CHECKS):
            errors.append(f"reviews[{index}] has an empty rationale")
    if review_keys != raw_keys:
        errors.append("manual review targets do not exactly match eligible scan targets")
    return errors


def _metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for check in CHECKS:
        values = {"positive_labels": 0, "negative_labels": 0, "TP": 0, "FP": 0, "FN": 0, "TN": 0}
        for row in rows:
            expected = row["labels"][check]
            observed = check in row["findings"]
            values["positive_labels" if expected else "negative_labels"] += 1
            if expected and observed:
                values["TP"] += 1
            elif expected:
                values["FN"] += 1
            elif observed:
                values["FP"] += 1
            else:
                values["TN"] += 1
        predicted_positive = values["TP"] + values["FP"]
        actual_positive = values["TP"] + values["FN"]
        metrics[check] = {
            **values,
            "precision": values["TP"] / predicted_positive if predicted_positive else None,
            "recall": values["TP"] / actual_positive if actual_positive else None,
        }
    return metrics


def _format_number(value: Any) -> str:
    return "null" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)


def _render_results(payload: dict[str, Any]) -> str:
    lines = [
        "# Current public-repository audit",
        "",
        f"Selection completed: {payload['selected_at']}",
        f"All scan attempts completed: {payload['scan_completed_at']}",
        f"Manual review completed: {payload['reviewed_at']}",
        f"Tool version: {payload['tool_version']}",
        f"Selected / eligible / excluded: {payload['selected_targets']} / {payload['eligible_targets']} / {payload['excluded_targets']}",
        "",
        "Repositories were selected first, every selected HEAD commit was attempted second, and manual labels were assigned only after all attempts finished. Excluded targets are not included in classification metrics.",
        "",
        "This is a stratified snapshot of 30 small, recently pushed public repositories across six language buckets. It is not a statistically representative sample of all GitHub repositories.",
        "",
        "## Metrics",
        "",
        "| Check | + | - | TP | FP | FN | TN | Precision | Recall |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for check, values in payload["metrics"].items():
        lines.append(
            f"| `{check}` | {values['positive_labels']} | {values['negative_labels']} | "
            f"{values['TP']} | {values['FP']} | {values['FN']} | {values['TN']} | "
            f"{_format_number(values['precision'])} | {_format_number(values['recall'])} |"
        )
    for heading, key in (("False positives", "false_positives"), ("False negatives", "false_negatives")):
        lines.extend(["", f"## {heading}", ""])
        if not payload[key]:
            lines.append("- None")
        else:
            for row in payload[key]:
                lines.append(
                    f"- `{row['full_name']}` `{row['commit']}` — observed `{row['findings']}`; labels `{row['labels']}`"
                )
    lines.extend(["", "## Excluded targets", ""])
    if not payload["excluded_results"]:
        lines.append("- None")
    else:
        for row in payload["excluded_results"]:
            lines.append(
                f"- `{row['full_name']}` `{row['commit']}` — stage `{row['error_stage']}`: {row['error'] or 'unknown error'}"
            )
    lines.extend(["", "## Reviewed repositories", ""])
    for row in payload["results"]:
        lines.extend(
            [
                f"### {row['full_name']}",
                "",
                f"- Commit: `{row['commit']}`",
                f"- Language bucket: {row['language_bucket']}",
                f"- Doctor project type: `{row.get('detected_project_type')}`",
                f"- Doctor findings: `{row['findings']}`",
                f"- `missing-start-entrypoint` label: `{str(row['labels']['missing-start-entrypoint']).lower()}` — {row['rationale']['missing-start-entrypoint']}",
                f"- `readme-missing-verification` label: `{str(row['labels']['readme-missing-verification']).lower()}` — {row['rationale']['readme-missing-verification']}",
                "",
            ]
        )
    return "\n".join(lines)


def publish_review() -> dict[str, Any]:
    raw = _read_json(RAW_PATH)
    review = _read_json(REVIEW_PATH)
    errors = validate_review(raw, review)
    if errors:
        raise RuntimeError("; ".join(errors))
    reviews = {(item["repository"], item["commit"]): item for item in review["reviews"]}
    rows: list[dict[str, Any]] = []
    excluded_results: list[dict[str, Any]] = []
    for raw_row in raw["results"]:
        if not _eligible_audit_row(raw_row):
            error = raw_row.get("execution_error")
            excluded_results.append(
                {
                    "full_name": raw_row["full_name"],
                    "repository": raw_row["repository"],
                    "commit": raw_row["commit"],
                    "language_bucket": raw_row["language_bucket"],
                    "error_stage": error.get("stage") if isinstance(error, dict) else None,
                    "error": error.get("stderr") if isinstance(error, dict) else None,
                }
            )
            continue
        key = (raw_row["repository"], raw_row["commit"])
        reviewed = reviews[key]
        rows.append(
            {
                "full_name": raw_row["full_name"],
                "repository": raw_row["repository"],
                "commit": raw_row["commit"],
                "language_bucket": raw_row["language_bucket"],
                "default_branch": raw_row["default_branch"],
                "detected_project_type": raw_row.get("detected_project_type"),
                "start_commands": raw_row.get("start_commands", []),
                "verification_commands": raw_row.get("verification_commands", []),
                "findings": raw_row.get("findings", []),
                "labels": reviewed["labels"],
                "rationale": reviewed["rationale"],
            }
        )
    metrics = _metrics(rows)
    false_positives = [
        row
        for row in rows
        if any(not row["labels"][check] and check in row["findings"] for check in CHECKS)
    ]
    false_negatives = [
        row
        for row in rows
        if any(row["labels"][check] and check not in row["findings"] for check in CHECKS)
    ]
    payload = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "selected_at": raw["selected_at"],
        "scan_completed_at": raw["scan_completed_at"],
        "reviewed_at": review["reviewed_at"],
        "tool_version": raw["tool_version"],
        "selected_targets": raw["targets"],
        "eligible_targets": len(rows),
        "excluded_targets": len(excluded_results),
        "workflow_order": ["selection", "all scan attempts", "manual review", "metric publication"],
        "selection_policy": raw["selection_policy"],
        "metrics": metrics,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "excluded_results": excluded_results,
        "results": rows,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(RESULTS_DIR / "latest.json", payload)
    (RESULTS_DIR / "latest.md").write_text(_render_results(payload), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    select_parser = subparsers.add_parser("select")
    select_parser.add_argument("--force", action="store_true")
    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("--force", action="store_true")
    scan_parser.add_argument("--resume", action="store_true")
    subparsers.add_parser("packet")
    subparsers.add_parser("publish")
    args = parser.parse_args(argv)
    try:
        if args.command == "select":
            payload = select_repositories(force=args.force)
            print(f"selected {len(payload['repositories'])} repositories")
        elif args.command == "scan":
            payload = scan_selection(force=args.force, resume=args.resume)
            print(
                f"attempted={payload['processed_targets']} "
                f"eligible={payload['eligible_targets']} "
                f"excluded={payload['excluded_targets']}"
            )
        elif args.command == "packet":
            print(build_review_packet())
        else:
            payload = publish_review()
            print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
