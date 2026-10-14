from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import CHECK_IDS, NON_IGNORABLE_CHECK_IDS, PROJECT_TYPES

DEFAULT_IGNORE_PATHS = (
    "**/.git/**",
    "**/node_modules/**",
    "**/vendor/**",
    "**/venv/**",
    "**/.venv/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/.tox/**",
    "**/.nox/**",
    "**/.next/**",
    "**/.nuxt/**",
    "**/.svelte-kit/**",
    "**/dist/**",
    "**/build/**",
    "**/coverage/**",
    "**/htmlcov/**",
    "**/logs/**",
    "**/reports/**",
    "**/doctor-output/**",
    "**/.benchmark-cache/**",
    "**/.current-audit-cache/**",
)

CONFIG_KEYS = frozenset(
    {
        "accepted_generated_paths",
        "expected_health_endpoints",
        "expected_ports",
        "expected_start_commands",
        "ignore_checks",
        "ignore_paths",
        "max_file_bytes",
        "max_files",
        "max_paths",
        "project_type",
    }
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
    max_paths: int = 100_000
    max_file_bytes: int = 1_000_000


def _string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be an array of strings")
    return tuple(item.replace("\\", "/").strip() for item in value if item.strip())


def _port_tuple(data: dict[str, Any], key: str) -> tuple[int, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(type(item) is int for item in value):
        raise ValueError(f"{key} must be an array of integers")
    for port in value:
        if not 1 <= port <= 65535:
            raise ValueError(f"Invalid port in {key}: {port}")
    return tuple(sorted(set(value)))


def _positive_int(data: dict[str, Any], key: str, default: int, minimum: int = 1) -> int:
    value = data.get(key, default)
    if type(value) is not int or value < minimum:
        raise ValueError(f"{key} must be an integer of at least {minimum}")
    return value


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

    unknown_keys = sorted(set(data) - CONFIG_KEYS)
    if unknown_keys:
        raise ValueError(f"Unknown configuration keys: {', '.join(unknown_keys)}")

    project_type = data.get("project_type", "auto")
    if project_type not in PROJECT_TYPES:
        choices = ", ".join(sorted(PROJECT_TYPES))
        raise ValueError(f"project_type must be one of: {choices}")

    ignore_checks = _string_tuple(data, "ignore_checks")
    unknown_checks = sorted(set(ignore_checks) - CHECK_IDS)
    if unknown_checks:
        raise ValueError(f"Unknown ignore_checks values: {', '.join(unknown_checks)}")
    forbidden_checks = sorted(set(ignore_checks) & NON_IGNORABLE_CHECK_IDS)
    if forbidden_checks:
        raise ValueError(
            "These safety checks cannot be ignored: " + ", ".join(forbidden_checks)
        )

    extra_ignores = _string_tuple(data, "ignore_paths")
    return DoctorConfig(
        ignore_paths=tuple(dict.fromkeys((*DEFAULT_IGNORE_PATHS, *extra_ignores))),
        ignore_checks=ignore_checks,
        expected_ports=_port_tuple(data, "expected_ports"),
        expected_start_commands=_string_tuple(data, "expected_start_commands"),
        expected_health_endpoints=_string_tuple(data, "expected_health_endpoints"),
        accepted_generated_paths=_string_tuple(data, "accepted_generated_paths"),
        project_type=project_type,
        max_files=_positive_int(data, "max_files", 10_000),
        max_paths=_positive_int(data, "max_paths", 100_000),
        max_file_bytes=_positive_int(data, "max_file_bytes", 1_000_000, minimum=1_000),
    )
