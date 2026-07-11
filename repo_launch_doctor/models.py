from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SEVERITY_ORDER = {"BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
SEVERITY_WEIGHTS = {"BLOCKER": 40, "HIGH": 20, "MEDIUM": 8, "LOW": 2, "INFO": 0}


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
    root: str
    generated_at: str
    files_scanned: int
    findings: list[Finding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

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
    def score(self) -> int:
        deduction = sum(SEVERITY_WEIGHTS[finding.severity] for finding in self.findings)
        return max(0, 100 - deduction)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "generated_at": self.generated_at,
            "files_scanned": self.files_scanned,
            "score": self.score,
            "counts": self.counts,
            "metadata": self.metadata,
            "findings": [asdict(finding) for finding in self.sorted_findings()],
        }
