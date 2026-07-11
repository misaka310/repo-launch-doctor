from __future__ import annotations

import fnmatch
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import DoctorConfig

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
    files: tuple[Path, ...]
    tracked_files: frozenset[str] | None
    skipped_files: int

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None


def path_matches(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    for raw_pattern in patterns:
        pattern = raw_pattern.replace("\\", "/").lstrip("./")
        prefix = pattern[:-3] if pattern.endswith("/**") else None
        if prefix and (normalized == prefix or normalized.startswith(prefix + "/")):
            return True
        if fnmatch.fnmatchcase(normalized, pattern):
            return True
    return False


def _tracked_files(root: Path) -> frozenset[str] | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    values = completed.stdout.decode("utf-8", errors="replace").split("\0")
    return frozenset(value.replace("\\", "/") for value in values if value)


def collect_inventory(root: Path, config: DoctorConfig) -> Inventory:
    resolved_root = root.expanduser().resolve()
    if not resolved_root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")

    files: list[Path] = []
    skipped = 0

    for current_dir, dirnames, filenames in os.walk(resolved_root, followlinks=False):
        current = Path(current_dir)
        retained_dirs: list[str] = []
        for dirname in dirnames:
            candidate = current / dirname
            relative = candidate.relative_to(resolved_root).as_posix()
            if candidate.is_symlink() or path_matches(relative, config.ignore_paths):
                skipped += 1
                continue
            retained_dirs.append(dirname)
        dirnames[:] = retained_dirs

        for filename in filenames:
            candidate = current / filename
            relative = candidate.relative_to(resolved_root).as_posix()
            if path_matches(relative, config.ignore_paths) or candidate.is_symlink():
                skipped += 1
                continue
            try:
                if candidate.stat().st_size > config.max_file_bytes:
                    skipped += 1
                    continue
            except OSError:
                skipped += 1
                continue
            if candidate.suffix.casefold() in BINARY_SUFFIXES:
                skipped += 1
                continue
            files.append(candidate)
            if len(files) >= config.max_files:
                return Inventory(
                    root=resolved_root,
                    files=tuple(sorted(files)),
                    tracked_files=_tracked_files(resolved_root),
                    skipped_files=skipped,
                )

    return Inventory(
        root=resolved_root,
        files=tuple(sorted(files)),
        tracked_files=_tracked_files(resolved_root),
        skipped_files=skipped,
    )
