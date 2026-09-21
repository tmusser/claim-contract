from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .metadata import (
    RULE_TRACE_SCHEMA_VERSION,
    RULE_TRACE_TYPE,
    TOOL_NAME,
    TOOL_VERSION,
)
from .models import NOT_EVALUATED, Finding
from .profiles import get_profile_manifest
from .validator import (
    TRACE_NOT_APPLICABLE,
    TRACE_PASS,
    TRACE_TRIGGERED,
    RuleEvaluation,
    validate_contract_with_trace,
)

TRACE_SCOPE_NOTICE = (
    "This trace records how implemented claim-contract rule predicates applied to the "
    "submitted declarations. PASS means only that an applicable rule emitted no finding; "
    "NOT_APPLICABLE means its predicate did not apply. This is not scientific validation."
)


@dataclass(frozen=True)
class RuleTraceEntry:
    rule_id: str
    severity: str
    status: str
    consumed_fields: tuple[str, ...]
    profile_trigger: str
    known_boundary: str
    reason: str
    findings: tuple[Finding, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.rule_id,
            "severity": self.severity,
            "status": self.status,
            "consumed_fields": list(self.consumed_fields),
            "profile_trigger": self.profile_trigger,
            "known_boundary": self.known_boundary,
            "reason": self.reason,
            "finding_count": len(self.findings),
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class RuleTrace:
    verdict: str
    profile: str
    claim_text: str
    contract_version: str | None
    input_binding: dict[str, Any] | None
    profile_manifest_binding: dict[str, Any] | None
    rules: tuple[RuleTraceEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        triggered = sum(rule.status == TRACE_TRIGGERED for rule in self.rules)
        passed = sum(rule.status == TRACE_PASS for rule in self.rules)
        not_applicable = sum(
            rule.status == TRACE_NOT_APPLICABLE for rule in self.rules
        )
        finding_count = sum(len(rule.findings) for rule in self.rules)

        contract: dict[str, Any] = {"profile": self.profile}
        if self.contract_version is not None:
            contract["version"] = self.contract_version
        if self.input_binding is not None:
            contract["input_binding"] = self.input_binding
        if self.profile_manifest_binding is not None:
            contract["profile_manifest_binding"] = self.profile_manifest_binding

        return {
            "schema_version": RULE_TRACE_SCHEMA_VERSION,
            "type": RULE_TRACE_TYPE,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "contract": contract,
            "verdict": self.verdict,
            "profile": self.profile,
            "claim_text": self.claim_text,
            "scientific_validation": False,
            "automatic_interpretation": False,
            "scope_notice": TRACE_SCOPE_NOTICE,
            "not_evaluated": list(NOT_EVALUATED),
            "summary": {
                "rule_count": len(self.rules),
                "triggered_count": triggered,
                "pass_count": passed,
                "not_applicable_count": not_applicable,
                "finding_count": finding_count,
            },
            "rules": [rule.to_dict() for rule in self.rules],
        }


def _build_entry(evaluation: RuleEvaluation, manifest) -> RuleTraceEntry:
    rule = manifest.rule(evaluation.rule_id)
    return RuleTraceEntry(
        rule_id=rule.rule_id,
        severity=rule.severity.value,
        status=evaluation.status,
        consumed_fields=rule.consumed_fields,
        profile_trigger=rule.trigger,
        known_boundary=rule.known_boundary,
        reason=evaluation.reason,
        findings=evaluation.findings,
    )


def build_rule_trace(contract: dict[str, Any]) -> RuleTrace:
    report, evaluations = validate_contract_with_trace(contract)
    profile_binding = report.resolved_profile_manifest_binding()
    manifest = get_profile_manifest(report.profile)

    return RuleTrace(
        verdict=report.verdict.value,
        profile=report.profile,
        claim_text=report.claim_text,
        contract_version=report.contract_version,
        input_binding=(
            report.input_binding.to_dict()
            if report.input_binding is not None
            else None
        ),
        profile_manifest_binding=(
            profile_binding.to_dict()
            if profile_binding is not None
            else None
        ),
        rules=tuple(
            _build_entry(evaluation, manifest)
            for evaluation in evaluations
        ),
    )


def format_rule_trace_text(trace: RuleTrace) -> str:
    lines = [
        f"Verdict: {trace.verdict}",
        f"Profile: {trace.profile}",
        "Scientific validation: false",
        "Automatic interpretation: false",
        "",
        "Rule trace:",
    ]

    for rule in trace.rules:
        lines.append(f"{rule.rule_id} {rule.severity} {rule.status}")
        lines.append(f"  Consumes: {', '.join(rule.consumed_fields)}")
        lines.append(f"  Reason: {rule.reason}")
        if rule.findings:
            for finding in rule.findings:
                lines.append(f"  Finding: {finding.path} — {finding.message}")

    lines.extend(
        [
            "",
            "Boundary: PASS does not establish that declarations are true, sufficient, or scientifically valid.",
        ]
    )
    return "\n".join(lines)
