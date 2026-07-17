from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .metadata import REPORT_SCHEMA_VERSION, REPORT_TYPE, TOOL_NAME, TOOL_VERSION


class Severity(str, Enum):
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class Verdict(str, Enum):
    READY = "READY"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


SCOPE_NOTICE = (
    "The submitted fields were checked against implemented minimum-contract rules. "
    "This is not scientific validation."
)

NOT_EVALUATED = [
    "whether the data are accurate, representative, or free of leakage",
    "whether the analysis code is correct or reproducible",
    "whether the model or statistical method is appropriate",
    "whether uncertainty estimates were computed correctly",
    "whether causal identifying assumptions are actually true",
    "whether the claim generalizes beyond the declared population and window",
    "whether the claim is useful, material, ethical, or decision-worthy",
]


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    path: str
    message: str
    action: str

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["severity"] = self.severity.value
        return result


@dataclass(frozen=True)
class Report:
    verdict: Verdict
    profile: str
    claim_text: str
    contract_version: str | None = None
    scientific_validation: bool = False
    scope_notice: str = SCOPE_NOTICE
    not_evaluated: list[str] = field(default_factory=lambda: list(NOT_EVALUATED))
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        findings = [finding.to_dict() for finding in self.findings]
        review_count = sum(
            finding.severity is Severity.REVIEW for finding in self.findings
        )
        block_count = sum(
            finding.severity is Severity.BLOCK for finding in self.findings
        )

        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "type": REPORT_TYPE,
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
            },
            "contract": {
                "version": self.contract_version,
                "profile": self.profile,
            },
            # Existing top-level fields remain for backward compatibility.
            "verdict": self.verdict.value,
            "profile": self.profile,
            "claim_text": self.claim_text,
            "scientific_validation": self.scientific_validation,
            "scope_notice": self.scope_notice,
            "not_evaluated": list(self.not_evaluated),
            "summary": {
                "finding_count": len(findings),
                "review_count": review_count,
                "block_count": block_count,
            },
            "findings": findings,
        }
