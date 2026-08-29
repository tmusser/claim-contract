from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .binding import (
    ContractBinding,
    ProfileManifestBinding,
    build_profile_manifest_binding,
)
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
    scientific_validation: bool = False
    scope_notice: str = SCOPE_NOTICE
    not_evaluated: list[str] = field(default_factory=lambda: list(NOT_EVALUATED))
    findings: list[Finding] = field(default_factory=list)
    # New additive fields stay after the original constructor surface so existing
    # positional callers keep their previous meaning.
    contract_version: str | None = None
    input_binding: ContractBinding | None = None
    profile_manifest_binding: ProfileManifestBinding | None = None

    def matches_contract(self, contract: dict[str, Any]) -> bool:
        """Return whether this report is bound to the supplied parsed contract."""

        if self.input_binding is None:
            return False
        return self.input_binding.matches_contract(contract)

    def resolved_profile_manifest_binding(self) -> ProfileManifestBinding | None:
        """Return the explicit or current supported-profile binding for this report.

        Reports without a contract input binding stay unbound. This avoids manufacturing
        ruleset identity for historical/manual report objects that were never produced by
        the bound validation path.
        """

        if self.profile_manifest_binding is not None:
            return self.profile_manifest_binding
        if self.input_binding is None:
            return None

        # Local import avoids a models <-> profiles import cycle.
        from .profiles import get_profile_manifest

        try:
            manifest = get_profile_manifest(self.profile)
        except ValueError:
            return None
        return build_profile_manifest_binding(manifest.to_dict())

    def to_dict(self) -> dict[str, Any]:
        findings = [finding.to_dict() for finding in self.findings]
        review_count = sum(
            finding.severity is Severity.REVIEW for finding in self.findings
        )
        block_count = sum(
            finding.severity is Severity.BLOCK for finding in self.findings
        )

        contract_metadata: dict[str, Any] = {
            "profile": self.profile,
        }
        if self.contract_version is not None:
            contract_metadata["version"] = self.contract_version
        if self.input_binding is not None:
            contract_metadata["input_binding"] = self.input_binding.to_dict()
        profile_manifest_binding = self.resolved_profile_manifest_binding()
        if profile_manifest_binding is not None:
            contract_metadata[
                "profile_manifest_binding"
            ] = profile_manifest_binding.to_dict()

        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "type": REPORT_TYPE,
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
            },
            "contract": contract_metadata,
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
