from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .metadata import (
    CHART_HANDOFF_SCHEMA_VERSION,
    CHART_HANDOFF_TYPE,
    TOOL_NAME,
    TOOL_VERSION,
)
from .models import Report, Severity, Verdict
from .validator import validate_contract


@dataclass(frozen=True)
class ChartHandoff:
    """Bound claim context that may be handed from claim-contract to chart-contract."""

    claim_text: str | None
    metric_name: str | None
    metric_unit: str | None
    population: str | None
    time_window: str | None
    provenance_source: str | None
    caveats: tuple[str, ...]
    report: Report

    def matches_contract(self, contract: dict[str, Any]) -> bool:
        """Return whether this handoff is still bound to the supplied contract."""

        return self.report.matches_contract(contract)

    def to_dict(self) -> dict[str, Any]:
        if self.report.input_binding is None:
            raise ValueError("Chart handoff requires a bound validation report.")

        findings = [finding.to_dict() for finding in self.report.findings]
        review_count = sum(
            finding.severity is Severity.REVIEW for finding in self.report.findings
        )
        block_count = sum(
            finding.severity is Severity.BLOCK for finding in self.report.findings
        )

        contract_metadata: dict[str, Any] = {
            "profile": self.report.profile,
            "input_binding": self.report.input_binding.to_dict(),
        }
        if self.report.contract_version is not None:
            contract_metadata["version"] = self.report.contract_version

        return {
            "schema_version": CHART_HANDOFF_SCHEMA_VERSION,
            "type": CHART_HANDOFF_TYPE,
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
            },
            "destination": {
                "tool": "chart-contract",
                "purpose": "bounded_claim_context",
            },
            "claim": {
                "text": self.claim_text,
                "metric": {
                    "name": self.metric_name,
                    "unit": self.metric_unit,
                },
                "population": self.population,
                "time_window": self.time_window,
            },
            "evidence_context": {
                "provenance_source": self.provenance_source,
                "caveats": list(self.caveats),
            },
            "validation": {
                "verdict": self.report.verdict.value,
                "profile": self.report.profile,
                "scientific_validation": self.report.scientific_validation,
                "scope_notice": self.report.scope_notice,
                "not_evaluated": list(self.report.not_evaluated),
                "summary": {
                    "finding_count": len(findings),
                    "review_count": review_count,
                    "block_count": block_count,
                },
                "findings": findings,
            },
            "contract": contract_metadata,
        }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _optional_string(value: Any, *, path: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ValueError(f"{path} must be a string or null for chart handoff export.")


def build_chart_handoff(contract: dict[str, Any]) -> ChartHandoff:
    """Validate a contract and build a conservative chart-contract handoff envelope."""

    report = validate_contract(contract)
    claim = _mapping(contract.get("claim"))
    metric = _mapping(claim.get("metric"))
    evidence = _mapping(contract.get("evidence"))
    provenance = _mapping(evidence.get("provenance"))

    caveats_value = evidence.get("caveats", [])
    if caveats_value is None:
        caveats_value = []
    if not isinstance(caveats_value, list) or not all(
        isinstance(item, str) for item in caveats_value
    ):
        raise ValueError("evidence.caveats must be an array of strings for chart handoff export.")

    return ChartHandoff(
        claim_text=_optional_string(claim.get("text"), path="claim.text"),
        metric_name=_optional_string(metric.get("name"), path="claim.metric.name"),
        metric_unit=_optional_string(metric.get("unit"), path="claim.metric.unit"),
        population=_optional_string(claim.get("population"), path="claim.population"),
        time_window=_optional_string(claim.get("time_window"), path="claim.time_window"),
        provenance_source=_optional_string(
            provenance.get("source"), path="evidence.provenance.source"
        ),
        caveats=tuple(caveats_value),
        report=report,
    )


def handoff_exit_code(handoff: ChartHandoff, *, warnings_as_errors: bool = False) -> int:
    """Mirror validation gate semantics for a generated chart handoff."""

    if handoff.report.verdict is Verdict.BLOCK:
        return 1
    if handoff.report.verdict is Verdict.REVIEW and warnings_as_errors:
        return 1
    return 0
