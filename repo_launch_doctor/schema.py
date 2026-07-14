"""Small, dependency-free validation for the published report-v1 schema."""
from __future__ import annotations

from typing import Any

from .constants import CHECK_IDS, SCHEMA_VERSION, SEVERITY_ORDER


def validate_report_payload(payload: object) -> list[str]:
    """Return validation errors for a report payload without importing a JSON Schema runtime."""
    if not isinstance(payload, dict):
        return ["report must be an object"]
    required = {"schema_version", "repository", "generated_at", "files_scanned", "paths_discovered", "verdict", "score", "counts", "metadata", "findings"}
    errors = [f"missing required field: {key}" for key in sorted(required - set(payload))]
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    if payload.get("verdict") not in {"PASS", "PASS_WITH_NOTES", "FAIL", "INCOMPLETE"}:
        errors.append("invalid verdict")
    if not isinstance(payload.get("repository"), str) or not payload["repository"]:
        errors.append("repository must be a non-empty string")
    for key in ("files_scanned", "paths_discovered"):
        if not isinstance(payload.get(key), int) or payload[key] < 0:
            errors.append(f"{key} must be a non-negative integer")
    score = payload.get("score")
    if payload.get("verdict") == "INCOMPLETE":
        if score is not None:
            errors.append("INCOMPLETE score must be null")
    elif not isinstance(score, int) or not 0 <= score <= 100:
        errors.append("complete report score must be an integer from 0 to 100")
    if not isinstance(payload.get("metadata"), dict) or not isinstance(payload.get("metadata", {}).get("scan_complete"), bool):
        errors.append("metadata.scan_complete must be a boolean")
    counts = payload.get("counts")
    if not isinstance(counts, dict) or set(counts) != set(SEVERITY_ORDER):
        errors.append("counts must contain every severity")
    findings = payload.get("findings")
    if not isinstance(findings, list):
        return errors + ["findings must be an array"]
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"findings[{index}] must be an object")
            continue
        expected = {"check_id", "severity", "title", "path", "evidence", "recommendation"}
        if set(finding) != expected:
            errors.append(f"findings[{index}] has an invalid shape")
            continue
        if finding["check_id"] not in CHECK_IDS:
            errors.append(f"findings[{index}] has unknown check_id")
        if finding["severity"] not in SEVERITY_ORDER:
            errors.append(f"findings[{index}] has invalid severity")
        if not all(isinstance(finding[key], str) for key in expected):
            errors.append(f"findings[{index}] fields must be strings")
    return errors
