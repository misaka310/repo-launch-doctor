from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .checks import _is_sensitive_path, _secret_candidate_requires_warning

_ZERO_SHA_RE = re.compile(r"^0+$")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<line>\d+)(?:,\d+)? @@")
_GENERIC_ASSIGNMENT_RE = re.compile(
    r"(?ix)^\s*(?:export\s+)?[\"']?(?P<key>(?:"
    r"[A-Z0-9_.-]*(?:api[_-]?key|access[_-]?key|client[_-]?secret|credential|"
    r"password|passwd|private[_-]?key|secret)[A-Z0-9_.-]*|"
    r"[A-Z0-9_.-]*(?:api|auth|access|refresh|bearer|github|secret)[_-]?token[A-Z0-9_.-]*|"
    r"token))[\"']?\s*[:=]\s*(?:"
    r"(?P<quote>[\"'])(?P<quoted_value>[^\"']{8,})(?P=quote)|"
    r"(?P<plain_value>[A-Za-z0-9_./+=:@-]{8,})"
    r")\s*[,;]?\s*(?:[#;].*)?$"
)
_SAFE_VALUE_RE = re.compile(
    r"(?i)^(?:changeme|change_me|replace(?:-me|_me)?|your[_-].*|example|sample|"
    r"dummy|test|fake|placeholder|redacted|none|null|true|false|<[^>]+>|"
    r"\$\{[^}]+\}|\{\{.*\}\}|x{6,}|\*{6,})$"
)

_SECRET_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "private-key",
        "BLOCKER",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "github-token",
        "BLOCKER",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,255}|github_pat_[A-Za-z0-9_]{50,255})\b"),
    ),
    (
        "openai-key",
        "BLOCKER",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "aws-access-key",
        "BLOCKER",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    (
        "google-api-key",
        "BLOCKER",
        re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ),
    (
        "slack-token",
        "BLOCKER",
        re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b"),
    ),
    (
        "stripe-live-key",
        "BLOCKER",
        re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{16,}\b"),
    ),
    (
        "credentialed-url",
        "HIGH",
        re.compile(r"(?i)\b(?:https?|ssh|git)://[^\s/:@]+:[^\s/@]+@[^\s]+"),
    ),
)


@dataclass(frozen=True)
class HistoryFinding:
    detector: str
    severity: str
    commit: str
    path: str
    line: int | None
    location: str
    evidence: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class HistoryScanReport:
    repository: str
    generated_at: str
    selection: str
    commits_scanned: int
    findings: list[HistoryFinding] = field(default_factory=list)
    binary_patches_skipped: int = 0

    @property
    def verdict(self) -> str:
        return "FAIL" if self.findings else "PASS"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "repository": self.repository,
            "generated_at": self.generated_at,
            "selection": self.selection,
            "commits_scanned": self.commits_scanned,
            "binary_patches_skipped": self.binary_patches_skipped,
            "verdict": self.verdict,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def _run_git_bytes(root: Path, args: Sequence[str]) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def _run_git_text(root: Path, args: Sequence[str]) -> str:
    return _run_git_bytes(root, args).decode("utf-8", errors="replace")


def _is_safe_generic_value(value: str) -> bool:
    cleaned = value.strip().strip("\"'")
    if _SAFE_VALUE_RE.fullmatch(cleaned):
        return True
    if cleaned.startswith(("${", "{{", "<")):
        return True
    if any(marker in cleaned.casefold() for marker in ("example", "sample", "dummy", "fake", "test")):
        return True
    if len(set(cleaned)) <= 2:
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9_]{7,}", cleaned):
        return True
    return False


def _detect_secret_types(text: str, *, path: str = "") -> list[tuple[str, str]]:
    detected: list[tuple[str, str]] = []
    for detector, severity, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            detected.append((detector, severity))
    assignment = _GENERIC_ASSIGNMENT_RE.match(text)
    if assignment:
        key = assignment.group("key").upper()
        value = assignment.group("quoted_value") or assignment.group("plain_value") or ""
        quoted = assignment.group("quoted_value") is not None
        looks_like_detector_constant = key.endswith(("_RE", "_REGEX", "_PATTERN", "_PATTERNS"))
        looks_like_metadata_name = key.endswith(("_PATH", "_FILE", "_FILENAME", "_NAME", "_ENV", "_VAR"))
        code_suffix = Path(path).suffix.casefold()
        code_file = code_suffix in {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java",
            ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".kts",
            ".c", ".cc", ".cpp", ".h", ".hpp", ".ps1", ".sh",
        }
        looks_like_code_reference = (
            not quoted
            and code_file
            and bool(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*", value))
        )
        path_parts = {part.casefold() for part in Path(path).parts}
        looks_like_short_test_fixture = (
            bool(path_parts & {"test", "tests", "fixture", "fixtures", "__fixtures__"})
            and quoted
            and len(value) <= 16
            and any(marker in value.casefold() for marker in ("secret", "password", "token", "key"))
        )
        if (
            not looks_like_detector_constant
            and not looks_like_metadata_name
            and not looks_like_code_reference
            and not looks_like_short_test_fixture
            and not _is_safe_generic_value(value)
        ):
            detected.append(("generic-secret-assignment", "HIGH"))
    return detected


def _normalize_diff_path(raw: str) -> str:
    value = raw.strip()
    if value == "/dev/null":
        return ""
    if value.startswith("b/"):
        value = value[2:]
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value.replace("\\", "/")


def _commit_list(
    root: Path,
    *,
    revision_range: str | None,
    all_history: bool,
    commits: Iterable[str] | None,
) -> tuple[list[str], str]:
    selected = sum(
        (
            revision_range is not None,
            all_history,
            commits is not None,
        )
    )
    if selected != 1:
        raise ValueError("Select exactly one of revision_range, all_history, or commits")

    if revision_range is not None:
        values = _run_git_text(root, ["rev-list", "--reverse", revision_range]).splitlines()
        return [value.strip() for value in values if value.strip()], revision_range
    if all_history:
        values = _run_git_text(root, ["rev-list", "--reverse", "--all"]).splitlines()
        return [value.strip() for value in values if value.strip()], "--all"

    unique: list[str] = []
    seen: set[str] = set()
    for value in commits or ():
        commit = value.strip()
        if not commit or _ZERO_SHA_RE.fullmatch(commit) or commit in seen:
            continue
        verified = _run_git_text(root, ["rev-parse", "--verify", f"{commit}^{{commit}}"]).strip()
        if verified not in seen:
            seen.add(verified)
            unique.append(verified)
    return unique, "explicit-commits"


def _changed_paths(root: Path, commit: str) -> list[str]:
    payload = _run_git_bytes(
        root,
        [
            "diff-tree",
            "--root",
            "--no-commit-id",
            "--name-status",
            "--no-renames",
            "-r",
            "-z",
            commit,
        ],
    )
    fields = payload.decode("utf-8", errors="replace").split("\0")
    paths: list[str] = []
    index = 0
    while index < len(fields):
        status = fields[index].strip()
        index += 1
        if not status or index >= len(fields):
            continue
        path = fields[index]
        index += 1
        if not status.startswith("D") and path:
            paths.append(path.replace("\\", "/"))
    return paths


def _scan_commit_message(commit: str, message: str) -> list[HistoryFinding]:
    findings: list[HistoryFinding] = []
    for line_number, line in enumerate(message.splitlines(), start=1):
        for detector, severity in _detect_secret_types(line):
            findings.append(
                HistoryFinding(
                    detector=detector,
                    severity=severity,
                    commit=commit[:12],
                    path="",
                    line=line_number,
                    location="commit-message",
                    evidence="A secret-like value was detected in the commit message; the value is redacted.",
                )
            )
    return findings


def _scan_patch(commit: str, patch: str) -> tuple[list[HistoryFinding], int]:
    findings: list[HistoryFinding] = []
    current_path = ""
    new_line: int | None = None
    binary_skipped = 0
    for raw_line in patch.splitlines():
        if raw_line.startswith("+++ "):
            current_path = _normalize_diff_path(raw_line[4:])
            new_line = None
            continue
        hunk = _HUNK_RE.match(raw_line)
        if hunk:
            new_line = int(hunk.group("line"))
            continue
        if raw_line.startswith("Binary files ") or raw_line.startswith("GIT binary patch"):
            binary_skipped += 1
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            content = raw_line[1:]
            for detector, severity in _detect_secret_types(content, path=current_path):
                findings.append(
                    HistoryFinding(
                        detector=detector,
                        severity=severity,
                        commit=commit[:12],
                        path=current_path,
                        line=new_line,
                        location="added-line",
                        evidence="A secret-like value was detected in added text; the value is redacted.",
                    )
                )
            if new_line is not None:
                new_line += 1
        elif raw_line.startswith(" ") and new_line is not None:
            new_line += 1
    return findings, binary_skipped


def _deduplicate(findings: Iterable[HistoryFinding]) -> list[HistoryFinding]:
    unique: list[HistoryFinding] = []
    seen: set[tuple[object, ...]] = set()
    for finding in findings:
        key = (
            finding.detector,
            finding.commit,
            finding.path,
            finding.line,
            finding.location,
        )
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique


def _historical_sensitive_path_requires_warning(root: Path, commit: str, path: str) -> bool:
    if not _is_sensitive_path(path):
        return False
    name = Path(path).name.casefold()
    if name in {".npmrc", ".pypirc", "firebase-config.js", "firebase-client-settings.js"} or name.startswith(".env."):
        try:
            text = _run_git_bytes(root, ["show", f"{commit}:{path}"]).decode(
                "utf-8", errors="replace"
            )
        except ValueError:
            text = None
        return _secret_candidate_requires_warning(path, text)
    return True


def scan_git_history(
    root: Path,
    *,
    revision_range: str | None = None,
    all_history: bool = False,
    commits: Iterable[str] | None = None,
    output_directory: Path | None = None,
) -> HistoryScanReport:
    root = root.expanduser().resolve()
    _run_git_text(root, ["rev-parse", "--is-inside-work-tree"])
    commit_ids, selection = _commit_list(
        root,
        revision_range=revision_range,
        all_history=all_history,
        commits=commits,
    )

    findings: list[HistoryFinding] = []
    binary_skipped = 0
    for commit in commit_ids:
        message = _run_git_text(root, ["show", "-s", "--format=%B", commit])
        findings.extend(_scan_commit_message(commit, message))
        for path in _changed_paths(root, commit):
            if _historical_sensitive_path_requires_warning(root, commit, path):
                findings.append(
                    HistoryFinding(
                        detector="sensitive-filename",
                        severity="BLOCKER",
                        commit=commit[:12],
                        path=path,
                        line=None,
                        location="tracked-path",
                        evidence="A sensitive-looking filename was introduced in this commit; contents are not included.",
                    )
                )
        patch = _run_git_text(
            root,
            [
                "show",
                "--format=",
                "--no-ext-diff",
                "--unified=0",
                "--no-renames",
                "--text",
                commit,
                "--",
            ],
        )
        patch_findings, skipped = _scan_patch(commit, patch)
        findings.extend(patch_findings)
        binary_skipped += skipped

    report = HistoryScanReport(
        repository=root.name,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        selection=selection,
        commits_scanned=len(commit_ids),
        findings=_deduplicate(findings),
        binary_patches_skipped=binary_skipped,
    )
    if output_directory is not None:
        write_history_report(report, output_directory)
    return report


def render_history_markdown(report: HistoryScanReport) -> str:
    lines = [
        "# Repo Launch Doctor history report",
        "",
        f"- Verdict: **{report.verdict}**",
        f"- Repository: `{report.repository}`",
        f"- Selection: `{report.selection}`",
        f"- Commits scanned: **{report.commits_scanned}**",
        f"- Binary patches not content-scanned: **{report.binary_patches_skipped}**",
        f"- Findings: **{len(report.findings)}**",
        "",
    ]
    if not report.findings:
        lines.append("No secret-like values or sensitive filenames were detected in the selected history.")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "| Severity | Detector | Commit | Location | Path | Line |",
            "|---|---|---|---|---|---:|",
        ]
    )
    for finding in report.findings:
        lines.append(
            "| {severity} | {detector} | `{commit}` | {location} | `{path}` | {line} |".format(
                severity=finding.severity,
                detector=finding.detector,
                commit=finding.commit,
                location=finding.location,
                path=finding.path or "(commit message)",
                line=finding.line if finding.line is not None else "",
            )
        )
    lines.extend(
        [
            "",
            "Detected values are intentionally redacted. Rotate or revoke any real credential before rewriting history.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_history_report(report: HistoryScanReport, output_directory: Path) -> None:
    output_directory = output_directory.expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "history-report.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_directory / "history-report.md").write_text(
        render_history_markdown(report),
        encoding="utf-8",
    )
