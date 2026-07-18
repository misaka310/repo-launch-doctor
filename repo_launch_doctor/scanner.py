from __future__ import annotations

import json
import re
import tomllib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .checks import run_checks
from .config import DoctorConfig, load_config
from .inventory import Inventory, collect_inventory, path_matches
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


def _read_root_readme(inventory: Inventory) -> str:
    for relative in sorted(inventory.all_file_paths, key=str.casefold):
        if "/" in relative.replace("\\", "/"):
            continue
        if Path(relative).name.casefold().startswith("readme"):
            return _read_optional_text(inventory, relative)
    return ""


def _is_dotnet_library(inventory: Inventory, paths: frozenset[str]) -> bool:
    project_paths = [
        path
        for path in paths
        if path.casefold().endswith(".csproj")
        and not path.casefold().startswith(("test/", "tests/", "examples/"))
    ]
    if not project_paths:
        return False
    project_texts = [_read_optional_text(inventory, path) for path in project_paths]
    return bool(project_texts) and not any(
        re.search(r"Sdk\s*=\s*[\"'][^\"']*Microsoft\.NET\.Sdk\.(?:Web|Worker)[^\"']*[\"']", text, re.IGNORECASE)
        or re.search(r"<OutputType>\s*(?:Exe|WinExe)\s*</OutputType>", text, re.IGNORECASE)
        or re.search(r"<Use(?:WPF|WindowsForms)>\s*true\s*</Use", text, re.IGNORECASE)
        for text in project_texts
    )


def _is_maven_aggregator(inventory: Inventory) -> bool:
    pom = _read_optional_text(inventory, "pom.xml")
    return bool(
        pom
        and re.search(r"<packaging>\s*pom\s*</packaging>", pom, re.IGNORECASE)
        and re.search(r"<modules(?:\s[^>]*)?>", pom, re.IGNORECASE)
    )


def _declared_non_application_type(inventory: Inventory) -> str | None:
    readme = _read_root_readme(inventory).casefold()
    if not readme:
        return None
    if re.search(r"\b(?:is|provides)\s+(?:an?\s+)?(?:[\w-]+\s+){0,4}(?:library|framework)\b", readme):
        return "library"
    if "source generator" in readme or "component library" in readme:
        return "library"
    collection_markers = (
        "documentation and operations workspace",
        "company command center",
        "knowledge base",
        "collection of solutions",
        "collection of examples",
        "course examples",
        "leetcode solutions",
        "coding exercises",
    )
    if any(marker in readme for marker in collection_markers):
        return "docs"
    return None


def _detect_project_type(inventory: Inventory, config: DoctorConfig) -> str:
    if config.project_type != "auto":
        return config.project_type

    paths = frozenset(
        path
        for path in inventory.all_file_paths
        if not path_matches(path, config.ignore_paths)
    )
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

    if _is_dotnet_library(inventory, paths) or _is_maven_aggregator(inventory):
        return "library"
    declared_type = _declared_non_application_type(inventory)
    if declared_type is not None:
        return declared_type
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


def _apply_static_assurance(metadata: dict[str, object]) -> None:
    complete = bool(metadata.get("scan_complete", True))
    git_tracking = bool(metadata.get("git_tracked_file_detection"))
    git_ignore = bool(metadata.get("git_ignore_detection"))
    metadata["assurance_level"] = "static"
    metadata["coverage"] = {
        "repository_files": "checked" if complete else "incomplete",
        "readme_and_entrypoints": "checked" if complete else "incomplete",
        "git_tracking": "checked" if git_tracking and git_ignore else "partial",
        "git_history": "not_checked",
        "runtime": "not_checked",
        "dependencies": "not_checked",
        "github_settings": "not_checked",
        "binary_contents": "not_checked",
    }


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
    _apply_static_assurance(metadata)

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
