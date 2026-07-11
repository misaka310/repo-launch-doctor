from __future__ import annotations

import fnmatch
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import DEFAULT_IGNORE_PATHS, DoctorConfig

BINARY_SUFFIXES = {
    ".7z",
    ".avi",
    ".bin",
    ".bmp",
    ".ckpt",
    ".dll",
    ".exe",
    ".flac",
    ".gif",
    ".ico",
    ".iso",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".pt",
    ".pth",
    ".pyc",
    ".safetensors",
    ".so",
    ".wav",
    ".webm",
    ".webp",
    ".zip",
}


@dataclass(frozen=True, slots=True)
class Inventory:
    root: Path
    readable_files: tuple[Path, ...]
    present_files: frozenset[str]
    present_directories: frozenset[str]
    tracked_files: frozenset[str] | None
    git_ignored_paths: frozenset[str] | None
    ignore_detection_source: str
    skipped_reasons: dict[str, int]
    scan_complete: bool
    incomplete_reasons: tuple[str, ...]
    scan_errors: tuple[str, ...]

    @property
    def all_file_paths(self) -> frozenset[str]:
        if self.tracked_files is None:
            return self.present_files
        return frozenset((*self.present_files, *self.tracked_files))

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None


def _normalize_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def path_matches(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = _normalize_relative_path(path)
    for raw_pattern in patterns:
        pattern = _normalize_relative_path(raw_pattern)
        if pattern.startswith("**/") and pattern.endswith("/**"):
            middle = pattern[3:-3].strip("/")
            padded = f"/{normalized}/"
            if (
                normalized == middle
                or normalized.startswith(middle + "/")
                or normalized.endswith("/" + middle)
                or f"/{middle}/" in padded
            ):
                return True
        prefix = pattern[:-3] if pattern.endswith("/**") else None
        if prefix and (normalized == prefix or normalized.startswith(prefix + "/")):
            return True
        if fnmatch.fnmatchcase(normalized, pattern):
            return True
    return False


def _tracked_files(root: Path, max_paths: int) -> tuple[frozenset[str] | None, bool]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None, True
    if completed.returncode != 0:
        return None, True
    values = [
        value.replace("\\", "/")
        for value in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if value
    ]
    complete = len(values) <= max_paths
    return frozenset(values[:max_paths]), complete


def _git_ignored_paths(root: Path, candidates: frozenset[str]) -> frozenset[str] | None:
    if not candidates:
        return frozenset()
    payload = ("\0".join(sorted(candidates)) + "\0").encode("utf-8")
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-z", "--stdin"],
            input=payload,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode not in {0, 1}:
        return None
    values = completed.stdout.decode("utf-8", errors="replace").split("\0")
    return frozenset(value.replace("\\", "/") for value in values if value)


def _gitignore_rule_matches(relative: str, raw_pattern: str) -> bool:
    pattern = raw_pattern
    if pattern.startswith("\\") and len(pattern) > 1 and pattern[1] in {"#", "!"}:
        pattern = pattern[1:]
    anchored = pattern.startswith("/")
    directory_only = pattern.endswith("/")
    pattern = pattern.strip("/")
    if not pattern:
        return False

    normalized = _normalize_relative_path(relative)
    parts = normalized.split("/") if normalized else []
    if "/" not in pattern:
        return any(fnmatch.fnmatchcase(part, pattern) for part in parts)

    if fnmatch.fnmatchcase(normalized, pattern):
        return True
    if not anchored and fnmatch.fnmatchcase(normalized, f"*/{pattern}"):
        return True
    if directory_only:
        return normalized == pattern or normalized.startswith(pattern + "/")
    return False


def _gitignore_fallback_paths(
    root: Path, candidates: frozenset[str]
) -> frozenset[str] | None:
    path = root / ".gitignore"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError):
        return None

    rules: list[tuple[bool, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        pattern = line[1:] if negated else line
        if pattern:
            rules.append((negated, pattern))

    ignored: set[str] = set()
    for relative in candidates:
        state = False
        for negated, pattern in rules:
            if _gitignore_rule_matches(relative, pattern):
                state = not negated
        if state:
            ignored.add(relative)
    return frozenset(ignored)


def collect_inventory(root: Path, config: DoctorConfig) -> Inventory:
    resolved_root = root.expanduser().resolve()
    if not resolved_root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")

    readable_files: list[Path] = []
    present_files: set[str] = set()
    present_directories: set[str] = set()
    skipped: dict[str, int] = {}
    incomplete_reasons: list[str] = []
    scan_errors: list[str] = []
    path_limit_reached = False
    content_limit_reached = False

    def increment(reason: str, amount: int = 1) -> None:
        skipped[reason] = skipped.get(reason, 0) + amount

    def on_walk_error(error: OSError) -> None:
        scan_errors.append(f"{type(error).__name__}: repository path could not be read")

    for current_dir, dirnames, filenames in os.walk(
        resolved_root, followlinks=False, onerror=on_walk_error
    ):
        current = Path(current_dir)
        retained_dirs: list[str] = []
        for dirname in dirnames:
            candidate = current / dirname
            relative = candidate.relative_to(resolved_root).as_posix()
            if dirname.casefold() == ".git":
                increment("git_metadata")
                continue
            present_directories.add(relative)
            if candidate.is_symlink():
                increment("symlink_directories")
                continue
            if path_matches(relative, DEFAULT_IGNORE_PATHS):
                increment("content_ignored_directories")
                continue
            retained_dirs.append(dirname)
        dirnames[:] = retained_dirs

        for filename in filenames:
            candidate = current / filename
            relative = candidate.relative_to(resolved_root).as_posix()
            if len(present_files) >= config.max_paths:
                path_limit_reached = True
                break
            present_files.add(relative)

            if path_matches(relative, config.ignore_paths):
                increment("content_ignored_files")
                continue
            if candidate.is_symlink():
                increment("symlink_files")
                continue
            try:
                size = candidate.stat().st_size
            except OSError:
                increment("unreadable_files")
                scan_errors.append(f"{relative}: metadata could not be read")
                continue
            if size > config.max_file_bytes:
                increment("large_files")
                continue
            if candidate.suffix.casefold() in BINARY_SUFFIXES:
                increment("binary_files")
                continue
            if len(readable_files) >= config.max_files:
                increment("content_file_limit")
                content_limit_reached = True
                continue
            readable_files.append(candidate)

        if path_limit_reached:
            break

    tracked_files, tracked_complete = _tracked_files(resolved_root, config.max_paths)
    if tracked_files is not None:
        # Tracked paths are security-relevant even when their directories are excluded
        # from content reading (for example build/ or node_modules/).
        present_files.update(path for path in tracked_files if (resolved_root / path).is_file())

    ignore_candidates = frozenset((*present_files, *present_directories))
    git_ignored_paths = (
        _git_ignored_paths(resolved_root, ignore_candidates)
        if tracked_files is not None
        else None
    )
    if git_ignored_paths is not None:
        ignore_detection_source = "git"
    else:
        git_ignored_paths = _gitignore_fallback_paths(resolved_root, ignore_candidates)
        ignore_detection_source = (
            ".gitignore-fallback" if git_ignored_paths is not None else "unavailable"
        )

    if path_limit_reached:
        incomplete_reasons.append(
            f"Path inventory reached max_paths={config.max_paths}; remaining paths were not enumerated."
        )
    if not tracked_complete:
        incomplete_reasons.append(
            f"Git tracked-file inventory reached max_paths={config.max_paths}; remaining tracked paths were not enumerated."
        )
    if content_limit_reached:
        incomplete_reasons.append(
            f"Readable content reached max_files={config.max_files}; some text files were not inspected."
        )
    if scan_errors:
        incomplete_reasons.append(
            f"{len(scan_errors)} filesystem item(s) could not be inspected."
        )

    return Inventory(
        root=resolved_root,
        readable_files=tuple(sorted(readable_files)),
        present_files=frozenset(present_files),
        present_directories=frozenset(present_directories),
        tracked_files=tracked_files,
        git_ignored_paths=git_ignored_paths,
        ignore_detection_source=ignore_detection_source,
        skipped_reasons=dict(sorted(skipped.items())),
        scan_complete=not incomplete_reasons,
        incomplete_reasons=tuple(incomplete_reasons),
        scan_errors=tuple(scan_errors),
    )
