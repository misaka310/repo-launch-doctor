from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .constants import SCHEMA_VERSION, SEVERITY_ORDER, SEVERITY_WEIGHTS


@dataclass(frozen=True, slots=True)
class Finding:
    check_id: str
    severity: str
    title: str
    path: str
    evidence: str
    recommendation: str

    def __post_init__(self) -> None:
        normalized = self.severity.upper()
        if normalized not in SEVERITY_ORDER:
            raise ValueError(f"Unsupported severity: {self.severity}")
        object.__setattr__(self, "severity", normalized)


@dataclass(slots=True)
class ScanReport:
    repository: str
    generated_at: str
    files_scanned: int
    paths_discovered: int
    findings: list[Finding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def sorted_findings(self) -> list[Finding]:
        return sorted(
            self.findings,
            key=lambda item: (
                SEVERITY_ORDER[item.severity],
                item.check_id,
                item.path.casefold(),
                item.title.casefold(),
            ),
        )

    @property
    def counts(self) -> dict[str, int]:
        counts = {severity: 0 for severity in SEVERITY_ORDER}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts

    @property
    def is_complete(self) -> bool:
        return bool(self.metadata.get("scan_complete", True))

    @property
    def verdict(self) -> str:
        if not self.is_complete:
            return "INCOMPLETE"
        severities = {finding.severity for finding in self.findings}
        if severities & {"BLOCKER", "HIGH"}:
            return "FAIL"
        if severities & {"MEDIUM", "LOW"}:
            return "PASS_WITH_NOTES"
        return "PASS"

    @property
    def score(self) -> int | None:
        if not self.is_complete:
            return None
        deduction = sum(SEVERITY_WEIGHTS[finding.severity] for finding in self.findings)
        return max(0, 100 - deduction)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repository": self.repository,
            "generated_at": self.generated_at,
            "files_scanned": self.files_scanned,
            "paths_discovered": self.paths_discovered,
            "verdict": self.verdict,
            "score": self.score,
            "counts": self.counts,
            "metadata": self.metadata,
            "findings": [asdict(finding) for finding in self.sorted_findings()],
        }
