from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

from .config import DoctorConfig
from .inventory import Inventory, path_matches
from .models import Finding

MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
PORT_PATTERNS = (
    re.compile(r"(?:localhost|127\.0\.0\.1):(?P<port>\d{2,5})", re.IGNORECASE),
    re.compile(r"\bport\b\s*[:=]\s*(?P<port>\d{2,5})", re.IGNORECASE),
    re.compile(r"\blisten\s*\(\s*(?P<port>\d{2,5})", re.IGNORECASE),
)
HEALTH_RE = re.compile(r"[\"'`](?P<endpoint>/(?:api/)?(?:health|status))[\"'`]", re.IGNORECASE)
README_NAMES = ("README.md", "README.MD", "readme.md", "README.txt")
START_FILE_NAMES = {
    "start.bat",
    "start.cmd",
    "start.ps1",
    "run.bat",
    "run.cmd",
    "run.ps1",
    "launch.bat",
    "launch.cmd",
    "launch.ps1",
    "app.py",
    "main.py",
}
SECRET_FILE_NAMES = {
    ".env",
    "cookies.txt",
    "credentials.json",
    "firebase-config.js",
    "id_rsa",
    "id_ed25519",
    "secrets.json",
    "config.local.json",
}
GENERATED_SEGMENTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "venv",
    ".venv",
    "logs",
    "dist",
    "build",
    "coverage",
}
GENERATED_SUFFIXES = {".log", ".tmp", ".dump", ".pyc"}


def _finding(
    check_id: str,
    severity: str,
    title: str,
    path: str,
    evidence: str,
    recommendation: str,
) -> Finding:
    return Finding(check_id, severity, title, path, evidence, recommendation)


def _readable_texts(inventory: Inventory) -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in inventory.files:
        text = inventory.read_text(path)
        if text is not None:
            texts[inventory.relative(path)] = text
    return texts


def _find_readme(texts: dict[str, str]) -> tuple[str, str] | None:
    for name in README_NAMES:
        if name in texts:
            return name, texts[name]
    for path, text in texts.items():
        if Path(path).name.casefold().startswith("readme"):
            return path, text
    return None


def _check_readme(texts: dict[str, str]) -> list[Finding]:
    readme = _find_readme(texts)
    if readme is None:
        return [
            _finding(
                "missing-readme",
                "HIGH",
                "README is missing",
                "README.md",
                "No README file was found.",
                "Add a README that explains the purpose, requirements, setup, usage, verification, and limitations.",
            )
        ]

    path, text = readme
    lowered = text.casefold()
    sections = {
        "requirements": ("requirements", "prerequisites", "必要", "要件"),
        "setup": ("setup", "install", "installation", "セットアップ", "導入"),
        "usage": ("usage", "quick start", "使い方", "起動"),
        "verification": ("test", "verification", "動作確認", "検証"),
        "limitations": ("limitations", "known issues", "制限", "注意"),
    }
    findings: list[Finding] = []
    for section, markers in sections.items():
        if not any(marker in lowered for marker in markers):
            severity = "MEDIUM" if section in {"setup", "usage", "verification"} else "LOW"
            findings.append(
                _finding(
                    f"readme-missing-{section}",
                    severity,
                    f"README does not clearly cover {section}",
                    path,
                    f"No recognizable {section} guidance was detected.",
                    f"Add a concise {section} section with copy-pasteable instructions.",
                )
            )
    return findings


def _markdown_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif " " in target:
        target = target.split(" ", 1)[0]
    return unquote(target.split("#", 1)[0].split("?", 1)[0])


def _check_markdown_links(inventory: Inventory, texts: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    for relative, text in texts.items():
        if Path(relative).suffix.casefold() not in {".md", ".markdown"}:
            continue
        source = inventory.root / relative
        for match in MARKDOWN_LINK_RE.finditer(text):
            raw_target = match.group(1)
            if raw_target.startswith(("http://", "https://", "mailto:", "data:", "#")):
                continue
            target = _markdown_link_target(raw_target)
            if not target:
                continue
            candidate = (inventory.root / target.lstrip("/")) if target.startswith("/") else (source.parent / target)
            try:
                resolved = candidate.resolve(strict=False)
                resolved.relative_to(inventory.root)
            except (OSError, ValueError):
                findings.append(
                    _finding(
                        "markdown-link-outside-root",
                        "MEDIUM",
                        "Markdown link escapes the repository",
                        relative,
                        f"The link target '{target}' resolves outside the scan root.",
                        "Use a repository-relative link or a full external URL.",
                    )
                )
                continue
            if not resolved.exists():
                findings.append(
                    _finding(
                        "broken-markdown-link",
                        "HIGH",
                        "Markdown link points to a missing file",
                        relative,
                        f"The local link target '{target}' does not exist.",
                        "Fix the path or add the referenced file.",
                    )
                )
    return findings


def _load_package_scripts(texts: dict[str, str]) -> dict[str, str]:
    raw = texts.get("package.json")
    if raw is None:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in scripts.items() if isinstance(value, str)}


def _detect_start_commands(texts: dict[str, str], scripts: dict[str, str]) -> list[str]:
    commands: list[str] = []
    for relative in texts:
        name = Path(relative).name.casefold()
        is_launcher = name in START_FILE_NAMES or (
            Path(name).suffix in {".bat", ".cmd", ".ps1"}
            and name.startswith(("start", "run", "launch", "open"))
        )
        if "/" not in relative and is_launcher:
            commands.append(relative)
    for name in ("start", "dev", "serve"):
        if name in scripts:
            commands.append("npm start" if name == "start" else f"npm run {name}")
    return sorted(set(commands))


def _detect_verification_commands(scripts: dict[str, str], texts: dict[str, str]) -> list[str]:
    commands: list[str] = []
    for name in ("test", "lint", "typecheck", "build", "check", "validate"):
        if name in scripts:
            commands.append("npm test" if name == "test" else f"npm run {name}")
    if "pyproject.toml" in texts or "pytest.ini" in texts:
        commands.append("python -m pytest")
    if any(path.startswith("tests/") and path.endswith(".py") for path in texts):
        commands.append("python -m unittest discover -s tests")
    return sorted(set(commands))


def _detect_ports(texts: dict[str, str]) -> list[int]:
    ports: set[int] = set()
    for text in texts.values():
        for pattern in PORT_PATTERNS:
            for match in pattern.finditer(text):
                port = int(match.group("port"))
                if 1 <= port <= 65535:
                    ports.add(port)
    return sorted(ports)


def _detect_health_endpoints(texts: dict[str, str]) -> list[str]:
    endpoints: set[str] = set()
    for text in texts.values():
        for match in HEALTH_RE.finditer(text):
            endpoints.add(match.group("endpoint"))
        for endpoint in ("/health", "/api/health", "/status", "/api/status"):
            if endpoint in text:
                endpoints.add(endpoint)
    return sorted(endpoints)


def _check_entrypoints(
    texts: dict[str, str], config: DoctorConfig, start_commands: list[str]
) -> list[Finding]:
    findings: list[Finding] = []
    if not start_commands and config.project_type not in {"library", "docs"}:
        findings.append(
            _finding(
                "missing-start-entrypoint",
                "HIGH",
                "No clear start entrypoint was detected",
                ".",
                "No root launcher or package start/dev script was found.",
                "Add one obvious launcher and document it in the README.",
            )
        )
    for command in config.expected_start_commands:
        normalized = command.replace("\\", "/")
        if normalized not in start_commands and normalized not in texts:
            findings.append(
                _finding(
                    "expected-start-command-missing",
                    "HIGH",
                    "Configured start command is missing",
                    normalized,
                    "The expected start command was not detected.",
                    "Add the entrypoint or update .repo-launch-doctor.json.",
                )
            )
    return findings


def _check_secret_risk(inventory: Inventory) -> list[Finding]:
    findings: list[Finding] = []
    for path in inventory.files:
        relative = inventory.relative(path)
        name = path.name.casefold()
        safe_env_example = bool(
            re.fullmatch(r"\.env(?:\.[a-z0-9_-]+)*\.(?:example|sample|template)", name)
        )
        risky = not safe_env_example and (
            name in SECRET_FILE_NAMES
            or name.startswith(".env.")
            or path.suffix.casefold() in {".pem", ".key", ".pfx", ".p12"}
        )
        if not risky:
            continue
        tracked = inventory.tracked_files is not None and relative in inventory.tracked_files
        findings.append(
            _finding(
                "secret-risk-file",
                "BLOCKER" if tracked else "HIGH",
                "Sensitive-looking file may be publishable",
                relative,
                "A sensitive-looking filename is present. Its contents were not included in the report.",
                "Remove it from version control, rotate exposed credentials if needed, and provide a safe example file.",
            )
        )
    return findings


def _check_generated_artifacts(inventory: Inventory, config: DoctorConfig) -> list[Finding]:
    findings: list[Finding] = []
    for path in inventory.files:
        relative = inventory.relative(path)
        if path_matches(relative, config.accepted_generated_paths):
            continue
        parts = {part.casefold() for part in Path(relative).parts}
        generated = bool(parts & GENERATED_SEGMENTS) or path.suffix.casefold() in GENERATED_SUFFIXES
        if not generated:
            continue
        tracked = inventory.tracked_files is not None and relative in inventory.tracked_files
        if tracked or inventory.tracked_files is None:
            findings.append(
                _finding(
                    "generated-artifact-present",
                    "MEDIUM",
                    "Generated or local artifact is present",
                    relative,
                    "The path resembles a log, cache, dependency tree, build output, or local runtime artifact.",
                    "Ignore it, remove it from Git, or declare the path in accepted_generated_paths when intentional.",
                )
            )
    return findings


def _is_web_project(texts: dict[str, str], config: DoctorConfig) -> bool:
    if config.project_type in {"web", "static-web"}:
        return True
    if config.project_type in {"desktop", "cli", "library", "docs"}:
        return False
    return "index.html" in texts or any(path.endswith("/index.html") for path in texts)


def _check_web_features(
    texts: dict[str, str], config: DoctorConfig, health_endpoints: list[str]
) -> list[Finding]:
    if not _is_web_project(texts, config):
        return []
    findings: list[Finding] = []
    favicon_files = [path for path in texts if Path(path).name.casefold().startswith("favicon.")]
    html_text = "\n".join(text for path, text in texts.items() if path.endswith(".html"))
    has_declaration = re.search(r"<link[^>]+rel=[\"'][^\"']*icon", html_text, re.IGNORECASE)
    if not favicon_files or not has_declaration:
        findings.append(
            _finding(
                "missing-favicon",
                "LOW",
                "Web app favicon is incomplete",
                "index.html",
                "A favicon file and matching <link rel='icon'> declaration were not both detected.",
                "Add a dedicated favicon file and reference it from the page head.",
            )
        )
    if config.project_type != "static-web" and not health_endpoints:
        findings.append(
            _finding(
                "missing-health-check",
                "MEDIUM",
                "No health endpoint was detected",
                ".",
                "No /health or /status route was found in readable source or documentation.",
                "Expose a lightweight local health endpoint and document the expected response.",
            )
        )
    return findings


def _check_public_docs(texts: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    names = {Path(path).name.casefold() for path in texts}
    if not any(name.startswith("license") for name in names):
        findings.append(
            _finding(
                "missing-license",
                "MEDIUM",
                "License file is missing",
                "LICENSE",
                "No license file was detected.",
                "Choose and add a license before public distribution.",
            )
        )
    if "security.md" not in names:
        findings.append(
            _finding(
                "missing-security-doc",
                "LOW",
                "Security guidance is missing",
                "SECURITY.md",
                "No SECURITY.md file was detected.",
                "Document secret handling, local-network exposure, and vulnerability reporting where relevant.",
            )
        )
    example_files = [
        path
        for path in texts
        if "example" in Path(path).name.casefold() or Path(path).name.casefold().endswith(".sample.json")
    ]
    if not example_files:
        findings.append(
            _finding(
                "missing-config-example",
                "LOW",
                "No safe configuration example was detected",
                ".",
                "No example or sample configuration file was found.",
                "Add a placeholder-only example when the project requires local configuration.",
            )
        )
    return findings


def _check_expected_capabilities(
    config: DoctorConfig, ports: list[int], health_endpoints: list[str]
) -> list[Finding]:
    findings: list[Finding] = []
    for port in config.expected_ports:
        if port not in ports:
            findings.append(
                _finding(
                    "expected-port-missing",
                    "MEDIUM",
                    "Configured port was not detected",
                    ".repo-launch-doctor.json",
                    f"Expected port {port} was not found in readable files.",
                    "Document or implement the port, or update the doctor configuration.",
                )
            )
    for endpoint in config.expected_health_endpoints:
        if endpoint not in health_endpoints:
            findings.append(
                _finding(
                    "expected-health-endpoint-missing",
                    "MEDIUM",
                    "Configured health endpoint was not detected",
                    ".repo-launch-doctor.json",
                    f"Expected endpoint '{endpoint}' was not found in readable files.",
                    "Implement and document the endpoint, or update the doctor configuration.",
                )
            )
    return findings


def run_checks(inventory: Inventory, config: DoctorConfig) -> tuple[list[Finding], dict[str, object]]:
    texts = _readable_texts(inventory)
    scripts = _load_package_scripts(texts)
    start_commands = _detect_start_commands(texts, scripts)
    verification_commands = _detect_verification_commands(scripts, texts)
    ports = _detect_ports(texts)
    health_endpoints = _detect_health_endpoints(texts)

    checks = (
        lambda: _check_readme(texts),
        lambda: _check_markdown_links(inventory, texts),
        lambda: _check_entrypoints(texts, config, start_commands),
        lambda: _check_secret_risk(inventory),
        lambda: _check_generated_artifacts(inventory, config),
        lambda: _check_web_features(texts, config, health_endpoints),
        lambda: _check_public_docs(texts),
        lambda: _check_expected_capabilities(config, ports, health_endpoints),
    )

    findings: list[Finding] = []
    for index, check in enumerate(checks, start=1):
        try:
            findings.extend(check())
        except Exception as exc:  # keep one broken check from hiding all other results
            findings.append(
                _finding(
                    "internal-check-error",
                    "MEDIUM",
                    "A doctor check could not complete",
                    ".",
                    f"Check {index} failed with {type(exc).__name__}.",
                    "Run the doctor with a minimal reproduction and report the failure.",
                )
            )

    ignored = set(config.ignore_checks)
    findings = [finding for finding in findings if finding.check_id not in ignored]

    metadata: dict[str, object] = {
        "project_type": (
            config.project_type
            if config.project_type != "auto"
            else ("web" if _is_web_project(texts, config) else "auto")
        ),
        "start_commands": start_commands,
        "verification_commands": verification_commands,
        "ports": ports,
        "health_endpoints": health_endpoints,
        "git_tracked_file_detection": inventory.tracked_files is not None,
        "skipped_files": inventory.skipped_files,
    }
    return findings, metadata
