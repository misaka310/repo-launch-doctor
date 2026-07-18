from __future__ import annotations

SCHEMA_VERSION = "1.0"
PACKAGE_VERSION = "0.4.0"

SEVERITY_ORDER = {"BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
SEVERITY_WEIGHTS = {"BLOCKER": 40, "HIGH": 20, "MEDIUM": 8, "LOW": 2, "INFO": 0}

CHECK_IDS = frozenset(
    {
        "broken-markdown-link",
        "expected-health-endpoint-missing",
        "expected-port-missing",
        "expected-start-command-missing",
        "generated-artifact-present",
        "internal-check-error",
        "markdown-link-outside-root",
        "missing-config-example",
        "missing-favicon",
        "missing-health-check",
        "missing-license",
        "missing-readme",
        "missing-security-doc",
        "missing-start-entrypoint",
        "readme-missing-limitations",
        "readme-missing-requirements",
        "readme-missing-setup",
        "readme-missing-usage",
        "readme-missing-verification",
        "scan-incomplete",
        "secret-risk-file",
    }
)

NON_IGNORABLE_CHECK_IDS = frozenset(
    {
        "internal-check-error",
        "scan-incomplete",
        "secret-risk-file",
    }
)

PROJECT_TYPES = frozenset({"auto", "web", "static-web", "desktop", "cli", "library", "docs"})
