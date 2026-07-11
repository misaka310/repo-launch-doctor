from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_IGNORE_PATHS = (
    ".git/**",
    "node_modules/**",
    "vendor/**",
    "venv/**",
    ".venv/**",
    "__pycache__/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    "dist/**",
    "build/**",
    "coverage/**",
    "reports/**",
    "doctor-output/**",
)


@dataclass(frozen=True, slots=True)
class DoctorConfig:
    ignore_paths: tuple[str, ...] = DEFAULT_IGNORE_PATHS
    ignore_checks: tuple[str, ...] = ()
    expected_ports: tuple[int, ...] = ()
    expected_start_commands: tuple[str, ...] = ()
    expected_health_endpoints: tuple[str, ...] = ()
    accepted_generated_paths: tuple[str, ...] = ()
    project_type: str = "auto"
    max_files: int = 10_000
    max_file_bytes: int = 1_000_000


def _string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be an array of strings")
    return tuple(item.replace("\\", "/").strip() for item in value if item.strip())


def _port_tuple(data: dict[str, Any], key: str) -> tuple[int, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
        raise ValueError(f"{key} must be an array of integers")
    for port in value:
        if not 1 <= port <= 65535:
            raise ValueError(f"Invalid port in {key}: {port}")
    return tuple(sorted(set(value)))


def load_config(root: Path) -> DoctorConfig:
    config_path = root / ".repo-launch-doctor.json"
    if not config_path.exists():
        return DoctorConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read {config_path.name}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{config_path.name} must contain a JSON object")

    project_type = data.get("project_type", "auto")
    if project_type not in {"auto", "web", "static-web", "desktop", "cli", "library", "docs"}:
        raise ValueError(
            "project_type must be auto, web, static-web, desktop, cli, library, or docs"
        )

    max_files = data.get("max_files", 10_000)
    max_file_bytes = data.get("max_file_bytes", 1_000_000)
    if not isinstance(max_files, int) or max_files < 1:
        raise ValueError("max_files must be a positive integer")
    if not isinstance(max_file_bytes, int) or max_file_bytes < 1_000:
        raise ValueError("max_file_bytes must be an integer of at least 1000")

    extra_ignores = _string_tuple(data, "ignore_paths")
    return DoctorConfig(
        ignore_paths=tuple(dict.fromkeys((*DEFAULT_IGNORE_PATHS, *extra_ignores))),
        ignore_checks=_string_tuple(data, "ignore_checks"),
        expected_ports=_port_tuple(data, "expected_ports"),
        expected_start_commands=_string_tuple(data, "expected_start_commands"),
        expected_health_endpoints=_string_tuple(data, "expected_health_endpoints"),
        accepted_generated_paths=_string_tuple(data, "accepted_generated_paths"),
        project_type=project_type,
        max_files=max_files,
        max_file_bytes=max_file_bytes,
    )
