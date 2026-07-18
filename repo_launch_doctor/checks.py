from __future__ import annotations

import json
import re
import tomllib
from configparser import ConfigParser, Error as ConfigParserError
from collections import Counter
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
FAVICON_DECLARATION_RE = re.compile(
    r"<link\b(?=[^>]*\brel\s*=\s*[\"'][^\"']*icon[^\"']*[\"'])[^>]*>",
    re.IGNORECASE,
)
HREF_RE = re.compile(r"\bhref\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
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
    ".npmrc",
    ".pypirc",
    "cookies.txt",
    "credentials.json",
    "firebase-config.js",
    "id_rsa",
    "id_ed25519",
    "secrets.json",
    "config.local.json",
    "service-account.json",
}
GENERATED_SEGMENTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".idea",
    "node_modules",
    "vendor",
    "venv",
    ".venv",
    "logs",
    "reports",
    "doctor-output",
    "dist",
    "build",
    "coverage",
    "htmlcov",
}
GENERATED_FILE_NAMES = {".ds_store", "desktop.ini", "thumbs.db"}
GENERATED_SUFFIXES = {".log", ".tmp", ".dump", ".pyc"}
BUILD_SOURCE_SUFFIXES = {
    ".bat",
    ".cmd",
    ".gradle",
    ".kts",
    ".md",
    ".props",
    ".ps1",
    ".py",
    ".sh",
    ".targets",
    ".toml",
    ".ts",
    ".tsx",
    ".xml",
    ".yaml",
    ".yml",
}
SENSITIVE_ENV_KEY_RE = re.compile(
    r"(?i)(?:^|[_-])(?:api[_-]?key|access[_-]?key|client[_-]?secret|credential|"
    r"password|passwd|private[_-]?key|secret|token)(?:$|[_-])"
)
SAFE_SECRET_VALUE_RE = re.compile(
    r"(?i)^(?:|changeme|change_me|replace(?:-me|_me)?|your[_ -].*|example|sample|"
    r"dummy|test|none|null|<[^>]+>|\$\{[^}]+\}|\{\{.*\}\}|\{%.*%\})$"
)
NPM_AUTH_KEY_RE = re.compile(r"(?i)(?:^|:)(?:_authToken|_password|_auth)$|^password$")
INLINE_CODE_RE = re.compile(r"`+[^`\n]*`+")
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
RUNTIME_EXCLUDED_PREFIXES = (
    ".github/",
    "docs/",
    "examples/",
    "fixtures/",
    "reports/",
    "test/",
    "tests/",
)
MARKDOWN_HEADING_RE = re.compile(r"^ {0,3}#{1,6}[ \t]+(?P<title>.+?)\s*#*\s*$")


README_VERIFICATION_COMMAND_RE = re.compile(
    r"(?im)(?:^|[`$>]\s*)(?:"
    r"python\s+-m\s+(?:pytest|unittest)\b|pytest\b|"
    r"(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:test|check|check:ci|lint|typecheck|build)\b|"
    r"ruff\s+check\b|mypy\b|go\s+test\b|dotnet\s+test\b|cargo\s+test\b|"
    r"mvn(?:w|\.cmd)?\s+(?:test|verify)\b|"
    r"(?:\.\/)?gradlew(?:\.bat)?\s+(?:test|check|build)\b|"
    r"make\s+(?:test|check|lint|verify)\b|"
    r"[\w.-]*build[\w.-]*\.bat\b"
    r")"
)
README_MANUAL_TEST_RE = re.compile(r"(?i)manual(?:ly)?\s+(?:test|testing|verify|verification)")
README_PREVIEW_COMMAND_RE = re.compile(
    r"(?i)(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:playground|preview|storybook)\b"
)
README_LAUNCH_COMMAND_RE = re.compile(
    r"(?i)^(?:"
    r"make\s+(?:run|start|serve|dev)\b.*|"
    r"docker(?:-compose|\s+compose)\s+up\b.*|docker\s+run\b.*|"
    r"dotnet\s+run\b.*|go\s+run\b.*|uvicorn\s+\S+.*|java\s+-jar\s+\S+.*|"
    r"(?:\.\/)?gradlew(?:\.bat)?\s+(?:run|bootrun)\b.*|"
    r"[\w.-]+\.bat\s+run\b.*"
    r")$"
)


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
    for path in inventory.readable_files:
        text = inventory.read_text(path)
        if text is not None:
            texts[inventory.relative(path)] = text
    return texts


def _runtime_texts(texts: dict[str, str]) -> dict[str, str]:
    runtime: dict[str, str] = {}
    for path, text in texts.items():
        lowered = path.casefold()
        name = Path(path).name.casefold()
        if lowered.startswith(RUNTIME_EXCLUDED_PREFIXES):
            continue
        if name.startswith("readme"):
            continue
        if "example" in name or "sample" in name or "template" in name:
            continue
        runtime[path] = text
    return runtime


def _find_readme(texts: dict[str, str]) -> tuple[str, str] | None:
    for name in README_NAMES:
        if name in texts:
            return name, texts[name]
    for path, text in texts.items():
        if Path(path).name.casefold().startswith("readme"):
            return path, text
    return None


def _readme_section_text(text: str) -> str:
    """Use Markdown headings, never prose or fenced code, as section evidence."""
    headings: list[str] = []
    labels: list[str] = []
    in_fence = False
    nonempty = [line for line in text.splitlines() if line.strip()]
    for line in text.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = MARKDOWN_HEADING_RE.match(line)
        if match:
            headings.append(match.group("title"))
        elif len(nonempty) <= 24 and re.match(
            r"^\s*(requirements?|prerequisites?|setup|installation|usage|testing|tests?|verification|limitations?|必要条件|要件|セットアップ|導入|使い方|使用方法|検証|動作確認|制限事項|注意事項)\s*[:：]",
            line,
            re.IGNORECASE,
        ):
            labels.append(line)
    return "\n".join((*headings, *labels)).casefold()


def _readme_has_verification_evidence(text: str) -> bool:
    headings = _readme_section_text(text)
    if any(
        marker in headings
        for marker in (
            "test",
            "verification",
            "validation",
            "quality",
            "quick check",
            "動作確認",
            "検証",
        )
    ):
        return True
    if README_VERIFICATION_COMMAND_RE.search(text):
        return True
    return bool(
        README_MANUAL_TEST_RE.search(text)
        and README_PREVIEW_COMMAND_RE.search(text)
    )


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
                "Add a README that explains purpose, requirements, setup, usage, verification, and limitations.",
            )
        ]

    path, text = readme
    lowered = _readme_section_text(text)
    sections = {
        "requirements": ("requirements", "prerequisites", "必要", "要件"),
        "setup": ("setup", "install", "installation", "セットアップ", "導入"),
        "usage": ("usage", "quick start", "使い方", "起動"),
        "verification": ("test", "verification", "動作確認", "検証"),
        "limitations": ("limitations", "known issues", "制限", "注意"),
    }
    findings: list[Finding] = []
    for section, markers in sections.items():
        present = (
            _readme_has_verification_evidence(text)
            if section == "verification"
            else any(marker in lowered for marker in markers)
        )
        if not present:
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


def _markdown_prose(text: str) -> str:
    lines: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in text.splitlines():
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence_character is not None:
            if (
                fence is not None
                and fence.group(1)[0] == fence_character
                and len(fence.group(1)) >= fence_length
            ):
                fence_character = None
                fence_length = 0
            lines.append("")
            continue
        if fence is not None:
            fence_character = fence.group(1)[0]
            fence_length = len(fence.group(1))
            lines.append("")
            continue
        lines.append(INLINE_CODE_RE.sub("", line))
    return "\n".join(lines)


def _check_markdown_links(inventory: Inventory, texts: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for relative, text in texts.items():
        if Path(relative).suffix.casefold() not in {".md", ".markdown"}:
            continue
        source = inventory.root / relative
        for match in MARKDOWN_LINK_RE.finditer(_markdown_prose(text)):
            raw_target = match.group(1).strip()
            if (
                not raw_target
                or raw_target.startswith(("#", "//"))
                or URI_SCHEME_RE.match(raw_target)
            ):
                continue
            target = _markdown_link_target(raw_target)
            if not target or (relative, target) in seen:
                continue
            if target.startswith("/") and not Path(target).suffix:
                continue
            seen.add((relative, target))
            candidate = (
                inventory.root / target.lstrip("/")
                if target.startswith("/")
                else source.parent / target
            )
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


def _load_package_data(texts: dict[str, str]) -> dict[str, object]:
    raw = texts.get("package.json")
    if raw is None:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _package_bin_commands(texts: dict[str, str]) -> list[str]:
    data = _load_package_data(texts)
    declared = data.get("bin")
    if isinstance(declared, dict):
        return sorted(
            str(name)
            for name, target in declared.items()
            if isinstance(name, str) and name.strip() and isinstance(target, str) and target.strip()
        )
    if isinstance(declared, str) and declared.strip():
        package_name = data.get("name")
        if isinstance(package_name, str) and package_name.strip():
            return [package_name.rsplit("/", 1)[-1]]
    return []


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
    return {str(key): value for key, value in scripts.items() if isinstance(value, str)}


def _load_pyproject(texts: dict[str, str]) -> dict[str, object]:
    raw = texts.get("pyproject.toml")
    if raw is None:
        return {}
    try:
        loaded = tomllib.loads(raw)
    except tomllib.TOMLDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _python_script_commands(texts: dict[str, str]) -> list[str]:
    data = _load_pyproject(texts)
    commands: list[str] = []
    project = data.get("project", {})
    if isinstance(project, dict):
        for key in ("scripts", "gui-scripts"):
            scripts = project.get(key, {})
            if isinstance(scripts, dict):
                commands.extend(
                    str(name)
                    for name, value in scripts.items()
                    if isinstance(value, str) and value.strip()
                )
    raw_setup_cfg = texts.get("setup.cfg")
    if raw_setup_cfg:
        parser = ConfigParser()
        try:
            parser.read_string(raw_setup_cfg)
            if parser.has_section("options.entry_points"):
                for key in ("console_scripts", "gui_scripts"):
                    if parser.has_option("options.entry_points", key):
                        for line in parser.get("options.entry_points", key).splitlines():
                            if "=" in line:
                                commands.append(line.split("=", 1)[0].strip())
        except ConfigParserError:
            pass
    return sorted(set(command for command in commands if command))


def _readme_launch_commands(texts: dict[str, str]) -> list[str]:
    readme = _find_readme(texts)
    if readme is None:
        return []
    _, text = readme
    candidates = list(text.splitlines())
    candidates.extend(re.findall(r"`([^`\n]+)`", text))
    commands: list[str] = []
    for candidate in candidates:
        normalized = candidate.strip().strip("`").strip()
        normalized = re.sub(r"^(?:[-+*]>?\s+|\d+[.)]\s+)", "", normalized)
        normalized = re.sub(r"^(?:\$|>)\s*", "", normalized).strip()
        if README_LAUNCH_COMMAND_RE.fullmatch(normalized):
            commands.append(normalized)
    return sorted(set(commands))


def _makefile_launch_commands(texts: dict[str, str]) -> list[str]:
    text = next(
        (value for path, value in texts.items() if path.casefold() == "makefile"),
        "",
    )
    commands: list[str] = []
    for match in re.finditer(r"(?im)^(run|start|serve|dev)\s*:(?![=])", text):
        commands.append(f"make {match.group(1).casefold()}")
    return commands


def _container_launch_commands(texts: dict[str, str]) -> list[str]:
    commands: list[str] = []
    for path, text in texts.items():
        normalized = path.casefold()
        if "/" not in path and normalized == "dockerfile":
            if re.search(r"(?im)^\s*entrypoint\s+", text):
                commands.append("Dockerfile ENTRYPOINT")
            elif re.search(r"(?im)^\s*cmd\s+", text):
                commands.append("Dockerfile CMD")
        if "/" not in path and normalized in {
            "compose.yml",
            "compose.yaml",
            "docker-compose.yml",
            "docker-compose.yaml",
        }:
            if re.search(r"(?im)^\s*services\s*:", text):
                commands.append("docker compose up")
    return commands


def _browser_extension_commands(texts: dict[str, str]) -> list[str]:
    for path, text in texts.items():
        if Path(path).name.casefold() != "manifest.json":
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("manifest_version"), int):
            return ["load browser extension"]
    return []


def _go_launch_commands(texts: dict[str, str]) -> list[str]:
    commands: list[str] = []
    for path, text in texts.items():
        normalized = path.replace("\\", "/")
        if Path(normalized).name.casefold() != "main.go":
            continue
        if normalized.casefold().startswith(RUNTIME_EXCLUDED_PREFIXES):
            continue
        if not re.search(r"(?m)^\s*package\s+main\b", text):
            continue
        parent = Path(normalized).parent.as_posix()
        commands.append("go run ." if parent == "." else f"go run ./{parent}")
    return commands


def _detect_start_commands(
    texts: dict[str, str], scripts: dict[str, str], config: DoctorConfig
) -> list[str]:
    commands: list[str] = []
    for relative in texts:
        name = Path(relative).name.casefold()
        is_descriptive_launcher = (
            Path(name).suffix in {".bat", ".cmd", ".ps1", ".sh"}
            and name.startswith(("start", "run", "launch", "open"))
            and not any(marker in name for marker in ("build", "install", "setup", "test"))
        )
        is_launcher = name in START_FILE_NAMES or is_descriptive_launcher
        if "/" not in relative and is_launcher:
            commands.append(relative)
    for name in ("start", "dev", "serve", "preview", "playground", "storybook"):
        if name in scripts:
            commands.append("npm start" if name == "start" else f"npm run {name}")
    commands.extend(_package_bin_commands(texts))
    commands.extend(_python_script_commands(texts))
    commands.extend(_makefile_launch_commands(texts))
    commands.extend(_container_launch_commands(texts))
    commands.extend(_browser_extension_commands(texts))
    commands.extend(_go_launch_commands(texts))
    commands.extend(_readme_launch_commands(texts))
    for relative in texts:
        normalized = relative.casefold()
        if (
            Path(relative).name.casefold() == "main.py"
            and not normalized.startswith(RUNTIME_EXCLUDED_PREFIXES)
        ):
            commands.append(f"python {relative}")
    if config.project_type == "static-web" and "index.html" in texts:
        commands.append("open index.html")
    return sorted(set(commands))


def _pytest_declared(texts: dict[str, str], pyproject: dict[str, object]) -> bool:
    if "pytest.ini" in texts or any(Path(path).name == "conftest.py" for path in texts):
        return True
    tool = pyproject.get("tool", {})
    if isinstance(tool, dict) and "pytest" in tool:
        return True
    project = pyproject.get("project", {})
    dependencies: list[object] = []
    if isinstance(project, dict):
        declared = project.get("dependencies", [])
        if isinstance(declared, list):
            dependencies.extend(declared)
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for values in optional.values():
                if isinstance(values, list):
                    dependencies.extend(values)
    return any(
        isinstance(value, str)
        and re.match(r"^pytest(?:[<>=!~ ;]|$)", value.strip(), re.IGNORECASE)
        for value in dependencies
    )


def _unittest_declared(texts: dict[str, str]) -> bool:
    return any(
        path.endswith(".py")
        and path.startswith(("tests/", "test/"))
        and (
            "unittest.TestCase" in text
            or "unittest.main(" in text
            or "from unittest" in text
            or "import unittest" in text
        )
        for path, text in texts.items()
    )


def _detect_verification_commands(
    scripts: dict[str, str], texts: dict[str, str]
) -> list[str]:
    commands: list[str] = []
    for name in ("test", "lint", "typecheck", "build", "check", "validate"):
        if name in scripts:
            commands.append("npm test" if name == "test" else f"npm run {name}")

    pyproject = _load_pyproject(texts)
    tool = pyproject.get("tool", {})
    if "tox.ini" in texts or (isinstance(tool, dict) and "tox" in tool):
        commands.append("tox")
    if "noxfile.py" in texts:
        commands.append("nox")
    if _pytest_declared(texts, pyproject):
        commands.append("python -m pytest")
    if _unittest_declared(texts):
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
    texts: dict[str, str],
    config: DoctorConfig,
    start_commands: list[str],
    project_type: str,
) -> list[Finding]:
    findings: list[Finding] = []
    if not start_commands and project_type not in {"library", "docs"}:
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


def _is_sensitive_path(relative: str) -> bool:
    path = Path(relative)
    name = path.name.casefold()
    safe_env_example = bool(
        re.fullmatch(r"\.env(?:\.[a-z0-9_-]+)*\.(?:example|sample|template)", name)
    )
    if safe_env_example:
        return False
    if name in SECRET_FILE_NAMES or name.startswith(".env."):
        return True
    if path.suffix.casefold() in {".pem", ".key", ".pfx", ".p12", ".kdbx"}:
        return True
    lowered = relative.casefold()
    return lowered.endswith("/.aws/credentials") or lowered == ".aws/credentials"


def _is_safe_public_config_value(value: str) -> bool:
    return bool(
        SAFE_SECRET_VALUE_RE.fullmatch(value)
        or re.fullmatch(r"(?i)(?:true|false|yes|no|on|off|-?\d+(?:\.\d+)?)", value)
        or URI_SCHEME_RE.match(value)
    )


def _secret_config_has_sensitive_value(text: str, *, npm_style: bool = False) -> bool:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        cleaned = value.strip().strip("\"'")
        sensitive_key = (
            bool(NPM_AUTH_KEY_RE.search(key))
            if npm_style
            else bool(SENSITIVE_ENV_KEY_RE.search(key))
        )
        if sensitive_key and not _is_safe_public_config_value(cleaned):
            return True
    return False


def _secret_candidate_requires_warning(relative: str, text: str | None) -> bool:
    name = Path(relative).name.casefold()
    if name in {".npmrc", ".pypirc"}:
        return text is None or _secret_config_has_sensitive_value(text, npm_style=True)
    if name.startswith(".env."):
        return text is None or _secret_config_has_sensitive_value(text)
    if name in {"firebase-config.js", "firebase-client-settings.js"}:
        if text is None:
            return True
        normalized = re.sub(r"\s+", " ", text).strip()
        return normalized != "export const firebaseConfig = null;"
    return True


def _check_secret_risk(inventory: Inventory) -> list[Finding]:
    findings: list[Finding] = []
    readable_texts = {
        inventory.relative(path): inventory.read_text(path)
        for path in inventory.readable_files
    }
    for relative in sorted(inventory.all_file_paths):
        if not _is_sensitive_path(relative):
            continue
        if not _secret_candidate_requires_warning(relative, readable_texts.get(relative)):
            continue
        tracked = inventory.tracked_files is not None and relative in inventory.tracked_files
        git_ignored = (
            inventory.git_ignored_paths is not None
            and relative in inventory.git_ignored_paths
        )
        if not tracked and git_ignored:
            continue
        severity = "BLOCKER" if tracked else "HIGH"
        state = (
            "tracked by Git"
            if tracked
            else "present and not confirmed as ignored by Git"
        )
        findings.append(
            _finding(
                "secret-risk-file",
                severity,
                "Sensitive-looking file may be publishable",
                relative,
                f"A sensitive-looking filename is {state}. Its contents were not read into the report.",
                "Remove it from version control, rotate exposed credentials if needed, and keep only a placeholder example.",
            )
        )
    return findings


def _generated_root(relative: str) -> str | None:
    normalized = relative.replace("\\", "/")
    if normalized.casefold().startswith(".github/"):
        return None
    path = Path(normalized)
    parts = path.parts
    for index, part in enumerate(parts):
        lowered = part.casefold()
        if lowered == "build" and path.suffix.casefold() in BUILD_SOURCE_SUFFIXES:
            continue
        if lowered in GENERATED_SEGMENTS:
            return Path(*parts[: index + 1]).as_posix()
    if path.name.casefold() in GENERATED_FILE_NAMES:
        return normalized
    if path.suffix.casefold() in GENERATED_SUFFIXES:
        return normalized
    return None


def _check_generated_artifacts(
    inventory: Inventory, config: DoctorConfig
) -> list[Finding]:
    findings: list[Finding] = []

    def accepted(path: str) -> bool:
        return path_matches(path, config.accepted_generated_paths)

    if inventory.tracked_files is not None:
        tracked_roots = Counter(
            root
            for relative in inventory.tracked_files
            if not accepted(relative)
            for root in [_generated_root(relative)]
            if root is not None
        )
        for path, count in sorted(tracked_roots.items()):
            findings.append(
                _finding(
                    "generated-artifact-present",
                    "MEDIUM",
                    "Generated or local artifact is tracked",
                    path,
                    f"Git tracks {count} generated/cache/log path(s) under this location.",
                    "Remove the paths from Git and add an ignore rule, or explicitly allow intentional generated assets.",
                )
            )

        ignored = inventory.git_ignored_paths or frozenset()
        tracked_root_names = set(tracked_roots)
        tracked_directories = {
            Path(*Path(relative).parts[:index]).as_posix()
            for relative in inventory.tracked_files
            for index in range(1, len(Path(relative).parts))
        }
        untracked_roots = Counter(
            root
            for relative in (*inventory.present_directories, *inventory.present_files)
            if relative not in inventory.tracked_files
            and not (
                relative in inventory.present_directories
                and relative in tracked_directories
            )
            and relative not in ignored
            and not accepted(relative)
            for root in [_generated_root(relative)]
            if root is not None and root not in tracked_root_names
        )
        for path, count in sorted(untracked_roots.items()):
            findings.append(
                _finding(
                    "generated-artifact-present",
                    "LOW",
                    "Generated or local artifact is not ignored",
                    path,
                    f"{count} generated/cache/log path(s) are untracked but not confirmed as ignored.",
                    "Add an ignore rule or explicitly allow the path when it is intentionally shareable.",
                )
            )
    else:
        roots: Counter[str] = Counter()
        ignored = inventory.git_ignored_paths or frozenset()
        for relative in inventory.present_directories:
            root = _generated_root(relative)
            if root and relative not in ignored and not accepted(relative):
                roots[root] += 1
        for relative in inventory.present_files:
            root = _generated_root(relative)
            if root and relative not in ignored and not accepted(relative):
                roots[root] += 1
        for path, count in sorted(roots.items()):
            findings.append(
                _finding(
                    "generated-artifact-present",
                    "MEDIUM",
                    "Generated or local artifact is present",
                    path,
                    f"{count} generated/cache/log path signal(s) were found, and Git tracking status was unavailable.",
                    "Check Git status, ignore local artifacts, or explicitly allow intentional generated assets.",
                )
            )
    return findings


def _is_web_project(
    texts: dict[str, str], all_paths: frozenset[str], config: DoctorConfig
) -> bool:
    if config.project_type in {"web", "static-web"}:
        return True
    if config.project_type in {"desktop", "cli", "library", "docs"}:
        return False
    relevant_paths = frozenset(
        path for path in all_paths if not path_matches(path, config.ignore_paths)
    )
    return "index.html" in relevant_paths or any(
        path.endswith("/index.html") for path in relevant_paths
    )


def _has_valid_favicon(
    texts: dict[str, str], all_paths: frozenset[str]
) -> bool:
    for html_path, text in texts.items():
        if not html_path.casefold().endswith(".html"):
            continue
        for tag_match in FAVICON_DECLARATION_RE.finditer(text):
            href_match = HREF_RE.search(tag_match.group(0))
            if href_match is None:
                continue
            href = unquote(
                href_match.group(1).split("#", 1)[0].split("?", 1)[0]
            ).strip()
            if not href or href.startswith(("http://", "https://", "data:")):
                continue
            if href.startswith("/"):
                target = href.lstrip("/")
            else:
                target = (Path(html_path).parent / href).as_posix()
            normalized = target.replace("\\", "/")
            while normalized.startswith("./"):
                normalized = normalized[2:]
            normalized = normalized.lstrip("/")
            if normalized in all_paths:
                return True
    return False


def _check_web_features(
    inventory: Inventory,
    texts: dict[str, str],
    config: DoctorConfig,
    health_endpoints: list[str],
) -> list[Finding]:
    if not _is_web_project(texts, inventory.all_file_paths, config):
        return []
    findings: list[Finding] = []
    if not _has_valid_favicon(texts, inventory.all_file_paths):
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
                "No /health or /status route was found in runtime source.",
                "Expose a lightweight local health endpoint and document the expected response.",
            )
        )
    return findings


def _needs_config_example(all_paths: frozenset[str], texts: dict[str, str]) -> bool:
    names = {Path(path).name.casefold() for path in all_paths}
    if any(name in SECRET_FILE_NAMES or name.startswith(".env") for name in names):
        return True
    runtime = _runtime_texts(texts)
    return any(
        re.search(r"\b(?:config|settings|environment variables?|env vars?)\b", text, re.IGNORECASE)
        for text in runtime.values()
    )


def _check_public_docs(
    inventory: Inventory, texts: dict[str, str]
) -> list[Finding]:
    findings: list[Finding] = []
    names = {Path(path).name.casefold() for path in inventory.all_file_paths}
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
                "Document secret handling and vulnerability reporting where relevant.",
            )
        )
    example_files = [
        path
        for path in inventory.all_file_paths
        if "example" in Path(path).name.casefold()
        or Path(path).name.casefold().endswith(".sample.json")
    ]
    if _needs_config_example(inventory.all_file_paths, texts) and not example_files:
        findings.append(
            _finding(
                "missing-config-example",
                "LOW",
                "No safe configuration example was detected",
                ".",
                "The project appears to use local configuration, but no example file was found.",
                "Add a placeholder-only example without real credentials or account data.",
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
                    f"Expected port {port} was not found in runtime source.",
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
                    f"Expected endpoint '{endpoint}' was not found in runtime source.",
                    "Implement and document the endpoint, or update the doctor configuration.",
                )
            )
    return findings


def _check_scan_completeness(inventory: Inventory) -> list[Finding]:
    if inventory.scan_complete:
        return []
    return [
        _finding(
            "scan-incomplete",
            "BLOCKER",
            "Repository scan was incomplete",
            ".",
            " ".join(inventory.incomplete_reasons),
            "Increase the configured limits or resolve unreadable paths, then run the scan again. Do not use a partial report for a release decision.",
        )
    ]


def _is_docs_only_repository(texts: dict[str, str], inventory: Inventory) -> bool:
    if _find_readme(texts) is None:
        return False
    documentation_suffixes = {
        ".adoc",
        ".gif",
        ".jpeg",
        ".jpg",
        ".md",
        ".pdf",
        ".png",
        ".rst",
        ".svg",
        ".txt",
        ".webp",
    }
    metadata_names = {".editorconfig", ".gitattributes", ".gitignore"}
    for relative in inventory.all_file_paths:
        normalized = relative.replace("\\", "/").casefold()
        path = Path(normalized)
        if normalized.startswith(".github/"):
            continue
        if path.name in metadata_names or path.name.startswith(("license", "readme")):
            continue
        if path.suffix in documentation_suffixes:
            continue
        return False
    return True


def _detected_project_type(
    texts: dict[str, str], inventory: Inventory, config: DoctorConfig
) -> str:
    if config.project_type != "auto":
        return config.project_type
    if _is_web_project(texts, inventory.all_file_paths, config):
        return "web"
    if _is_docs_only_repository(texts, inventory):
        return "docs"
    if "pyproject.toml" in texts and (
        "[project.scripts]" in texts["pyproject.toml"]
        or "repo_launch_doctor/__main__.py" in inventory.all_file_paths
    ):
        return "cli"
    return "auto"


def run_checks(
    inventory: Inventory, config: DoctorConfig
) -> tuple[list[Finding], dict[str, object]]:
    texts = _readable_texts(inventory)
    runtime_texts = _runtime_texts(texts)
    scripts = _load_package_scripts(texts)
    start_commands = _detect_start_commands(texts, scripts, config)
    verification_commands = _detect_verification_commands(scripts, texts)
    project_type = _detected_project_type(texts, inventory, config)
    web_project = _is_web_project(texts, inventory.all_file_paths, config)
    ports = (
        _detect_ports(runtime_texts)
        if web_project or config.expected_ports
        else []
    )
    health_endpoints = (
        _detect_health_endpoints(runtime_texts)
        if web_project or config.expected_health_endpoints
        else []
    )

    checks = (
        lambda: _check_scan_completeness(inventory),
        lambda: _check_readme(texts),
        lambda: _check_markdown_links(inventory, texts),
        lambda: _check_entrypoints(texts, config, start_commands, project_type),
        lambda: _check_secret_risk(inventory),
        lambda: _check_generated_artifacts(inventory, config),
        lambda: _check_web_features(
            inventory, texts, config, health_endpoints
        ),
        lambda: _check_public_docs(inventory, texts),
        lambda: _check_expected_capabilities(config, ports, health_endpoints),
    )

    findings: list[Finding] = []
    for index, check in enumerate(checks, start=1):
        try:
            findings.extend(check())
        except Exception as exc:  # one broken check must not hide all other results
            findings.append(
                _finding(
                    "internal-check-error",
                    "MEDIUM",
                    "A doctor check could not complete",
                    ".",
                    f"Check {index} failed with {type(exc).__name__}.",
                    "Run the doctor with a minimal synthetic reproduction and report the failure.",
                )
            )

    ignored = set(config.ignore_checks)
    suppressed = [finding for finding in findings if finding.check_id in ignored]
    findings = [finding for finding in findings if finding.check_id not in ignored]

    suppressed_counts = dict(
        sorted(Counter(finding.check_id for finding in suppressed).items())
    )
    metadata: dict[str, object] = {
        "project_type": project_type,
        "start_commands": start_commands,
        "verification_commands": verification_commands,
        "ports": ports,
        "health_endpoints": health_endpoints,
        "git_tracked_file_detection": inventory.tracked_files is not None,
        "git_ignore_detection": inventory.git_ignored_paths is not None,
        "ignore_detection_source": inventory.ignore_detection_source,
        "scan_complete": inventory.scan_complete,
        "incomplete_reasons": list(inventory.incomplete_reasons),
        "scan_errors": list(inventory.scan_errors),
        "skipped_reasons": inventory.skipped_reasons,
        "ignored_paths": list(config.ignore_paths),
        "ignored_checks": list(config.ignore_checks),
        "suppressed_findings": suppressed_counts,
    }
    return findings, metadata
