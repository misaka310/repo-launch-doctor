from __future__ import annotations

import json
import tomllib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .checks import run_checks
from .config import DoctorConfig, load_config
from .inventory import Inventory, collect_inventory
from .models import Finding, ScanReport
from .reporters import write_reports


def _read_optional_text(inventory: Inventory, relative: str) -> str:
    path = inventory.root / relative
    if relative not in inventory.all_file_paths:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def _detect_project_type(inventory: Inventory, config: DoctorConfig) -> str:
    if config.project_type != "auto":
        return config.project_type

    paths = inventory.all_file_paths
    lowered_paths = {path.casefold() for path in paths}
    package_json_text = _read_optional_text(inventory, "package.json")
    package_data: dict[str, object] = {}
    if package_json_text:
        try:
            loaded = json.loads(package_json_text)
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            package_data = loaded

    scripts = package_data.get("scripts", {})
    if not isinstance(scripts, dict):
        scripts = {}

    has_index = "index.html" in lowered_paths or any(
        path.endswith("/index.html") for path in lowered_paths
    )
    has_web_script = any(name in scripts for name in ("start", "dev", "serve"))
    has_server_source = any(
        Path(path).name.casefold()
        in {
            "server.py",
            "server.js",
            "server.ts",
            "app.py",
            "manage.py",
            "wsgi.py",
            "asgi.py",
        }
        for path in paths
    )
    if has_index:
        return "web" if has_web_script or has_server_source else "static-web"
    if has_web_script:
        return "web"

    if any(
        marker in lowered_paths
        for marker in ("mkdocs.yml", "mkdocs.yaml", "docs/conf.py", "_config.yml")
    ):
        return "docs"

    pyproject = _read_optional_text(inventory, "pyproject.toml")
    pyproject_data: dict[str, object] = {}
    if pyproject:
        try:
            parsed = tomllib.loads(pyproject)
            if isinstance(parsed, dict):
                pyproject_data = parsed
        except tomllib.TOMLDecodeError:
            pass
    project_table = pyproject_data.get("project", {})
    has_python_cli = isinstance(project_table, dict) and any(
        isinstance(project_table.get(key), dict) and project_table[key]
        for key in ("scripts", "gui-scripts")
    )
    if has_python_cli or any(
        path.endswith("/__main__.py") or path == "__main__.py"
        for path in lowered_paths
    ):
        return "cli"

    if isinstance(package_data.get("bin"), (str, dict)):
        return "cli"
    if any(key in package_data for key in ("main", "exports", "types", "typings")):
        return "library"

    has_python_package = any(
        path.endswith("/__init__.py")
        and (path.startswith("src/") or path.count("/") == 1)
        for path in lowered_paths
    )
    has_root_launcher = any(
        path in lowered_paths
        for path in (
            "app.py",
            "main.py",
            "start.bat",
            "start.cmd",
            "start.ps1",
            "run.bat",
            "run.cmd",
            "run.ps1",
        )
    )
    if pyproject and has_python_package and not has_root_launcher:
        return "library"

    return "auto"


def _preflight_text_errors(inventory: Inventory) -> list[str]:
    errors: list[str] = []
    for path in inventory.readable_files:
        try:
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            errors.append(inventory.relative(path))
    return sorted(errors)


def _mark_incomplete(
    findings: list[Finding],
    metadata: dict[str, object],
    text_errors: list[str],
) -> None:
    incomplete_reasons = list(metadata.get("incomplete_reasons", []))
    scan_errors = list(metadata.get("scan_errors", []))

    if text_errors:
        incomplete_reasons.append(
            f"{len(text_errors)} text file(s) could not be read as UTF-8."
        )
        scan_errors.extend(
            f"{path}: text content could not be read as UTF-8" for path in text_errors
        )

    internal_error_count = sum(
        finding.check_id == "internal-check-error" for finding in findings
    )
    if internal_error_count:
        incomplete_reasons.append(
            f"{internal_error_count} internal check(s) could not complete."
        )

    if not incomplete_reasons:
        return

    metadata["scan_complete"] = False
    metadata["incomplete_reasons"] = list(dict.fromkeys(incomplete_reasons))
    metadata["scan_errors"] = list(dict.fromkeys(scan_errors))

    findings[:] = [
        finding for finding in findings if finding.check_id != "scan-incomplete"
    ]
    findings.append(
        Finding(
            "scan-incomplete",
            "BLOCKER",
            "Repository scan was incomplete",
            ".",
            " ".join(metadata["incomplete_reasons"]),
            "Resolve unreadable files or failed checks, then run the scan again. Do not use a partial report for a release decision.",
        )
    )


def scan_repository(
    root: Path | str,
    output_directory: Path | str | None = None,
    *,
    include_absolute_path: bool = False,
) -> ScanReport:
    root_path = Path(root).expanduser().resolve()
    config = load_config(root_path)
    inventory = collect_inventory(root_path, config)
    text_errors = _preflight_text_errors(inventory)
    effective_config = replace(
        config, project_type=_detect_project_type(inventory, config)
    )
    findings, metadata = run_checks(inventory, effective_config)
    _mark_incomplete(findings, metadata, text_errors)

    repository_label = str(root_path) if include_absolute_path else (root_path.name or ".")
    report = ScanReport(
        repository=repository_label,
        generated_at=datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        files_scanned=len(inventory.readable_files),
        paths_discovered=len(inventory.all_file_paths),
        findings=findings,
        metadata=metadata,
    )
    if output_directory is not None:
        write_reports(report, Path(output_directory).expanduser().resolve())
    return report
