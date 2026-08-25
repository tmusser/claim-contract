from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .metadata import (
    PROFILE_MANIFEST_SCHEMA_VERSION,
    PROFILE_MANIFEST_TYPE,
    TOOL_NAME,
    TOOL_VERSION,
)
from .models import NOT_EVALUATED, SCOPE_NOTICE, Severity

DEFAULT_PROFILE = "minimum-v0.1"


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    severity: Severity
    consumed_fields: tuple[str, ...]
    trigger: str
    known_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.rule_id,
            "severity": self.severity.value,
            "consumed_fields": list(self.consumed_fields),
            "trigger": self.trigger,
            "known_boundary": self.known_boundary,
        }


@dataclass(frozen=True)
class ProfileManifest:
    name: str
    contract_schema: str
    description: str
    rules: tuple[RuleSpec, ...]

    def rule(self, rule_id: str) -> RuleSpec:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        raise KeyError(f"Unknown rule {rule_id!r} for profile {self.name!r}.")

    def to_dict(self) -> dict[str, Any]:
        rules = [rule.to_dict() for rule in self.rules]
        return {
            "schema_version": PROFILE_MANIFEST_SCHEMA_VERSION,
            "type": PROFILE_MANIFEST_TYPE,
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
            },
            "profile": {
                "name": self.name,
                "contract_schema": self.contract_schema,
                "description": self.description,
            },
            "scientific_validation": False,
            "scope_notice": SCOPE_NOTICE,
            "not_evaluated": list(NOT_EVALUATED),
            "rule_count": len(rules),
            "rules": rules,
        }


MINIMUM_V0_1 = ProfileManifest(
    name=DEFAULT_PROFILE,
    contract_schema="schemas/contract-minimum-v0.1.schema.json",
    description=(
        "Minimum declared evidence-to-language checks for analytical claims. "
        "The profile evaluates declarations, not underlying scientific correctness."
    ),
    rules=(
        RuleSpec(
            "CC001",
            Severity.BLOCK,
            (
                "claim.text",
                "claim.type",
                "claim.population",
                "claim.time_window",
                "claim.metric.name",
                "claim.metric.unit",
                "claim.metric.definition",
                "evidence.design",
                "evidence.sample_size",
                "evidence.provenance.source",
                "evidence.checks",
            ),
            "A required claim/evidence field is missing, or a basic required value is malformed.",
            "Checks declared completeness and simple supported values only; it does not verify the underlying evidence or provenance.",
        ),
        RuleSpec(
            "CC101",
            Severity.REVIEW,
            ("evidence.checks.metric_definition_locked",),
            "The metric definition is not declared locked.",
            "A true declaration is not proof that the metric definition was actually frozen before interpretation.",
        ),
        RuleSpec(
            "CC102",
            Severity.REVIEW,
            ("evidence.checks.missingness_assessed",),
            "Missingness is not declared assessed.",
            "The rule does not inspect missing data or determine whether the declared assessment was adequate.",
        ),
        RuleSpec(
            "CC201",
            Severity.BLOCK,
            (
                "claim.type",
                "claim.text",
                "claim.comparison.baseline",
                "claim.comparison.comparison",
            ),
            "A comparison or causal claim lacks explicit baseline and comparison groups.",
            "Group declarations do not establish comparability, exchangeability, or analytical validity.",
        ),
        RuleSpec(
            "CC202",
            Severity.BLOCK,
            (
                "claim.type",
                "claim.text",
                "evidence.estimate.scale",
                "evidence.estimate.baseline_value",
            ),
            "A relative or percentage comparison lacks a declared baseline value.",
            "The rule checks baseline presence, not whether the baseline or relative-effect calculation is correct.",
        ),
        RuleSpec(
            "CC203",
            Severity.REVIEW,
            (
                "claim.type",
                "claim.text",
                "evidence.estimate.value",
                "evidence.uncertainty",
            ),
            "A comparative or causal estimate is present without declared uncertainty information.",
            "The rule checks that uncertainty is declared, not whether it was computed correctly or is statistically appropriate.",
        ),
        RuleSpec(
            "CC204",
            Severity.REVIEW,
            (
                "evidence.design",
                "evidence.checks.composition_stability_assessed",
            ),
            "An observational before/after design lacks a declared composition-stability assessment.",
            "The rule does not verify that composition was actually stable or that the assessment was sufficient.",
        ),
        RuleSpec(
            "CC205",
            Severity.REVIEW,
            (
                "claim.type",
                "claim.text",
                "evidence.checks.multiple_comparisons_assessed",
                "evidence.multiplicity.comparisons",
                "evidence.multiplicity.adjustment",
                "evidence.multiplicity.rationale",
            ),
            "Comparison multiplicity is unassessed, malformed, or lacks an adjustment/rationale when multiple comparisons are declared.",
            "The harness cannot detect comparisons, outcomes, segments, or tests that were never declared.",
        ),
        RuleSpec(
            "CC206",
            Severity.BLOCK,
            (
                "claim.text",
                "evidence.estimate.value",
                "evidence.estimate.scale",
            ),
            "Qualitative magnitude language lacks a numeric estimate and declared scale.",
            "The rule does not decide whether a declared numeric effect is substantively large, small, meaningful, or material.",
        ),
        RuleSpec(
            "CC301",
            Severity.BLOCK,
            ("claim.type", "claim.text", "evidence.design"),
            "Causal claim language is paired with a design that is not eligible for causal claims in this profile.",
            "Causal-language detection is pattern-based and the design label is supplied by the contract; neither proves the actual design or analysis.",
        ),
        RuleSpec(
            "CC302",
            Severity.BLOCK,
            (
                "claim.type",
                "claim.text",
                "evidence.design",
                "evidence.checks.identifying_assumptions_documented",
            ),
            "A quasi-experimental causal claim lacks declared identifying assumptions.",
            "Documenting assumptions does not establish that those assumptions are true or that diagnostics support them.",
        ),
        RuleSpec(
            "CC303",
            Severity.BLOCK,
            (
                "claim.type",
                "claim.text",
                "evidence.design",
                "evidence.checks.treatment_assignment_validated",
            ),
            "A randomized causal claim lacks a declared treatment-assignment validation.",
            "The rule trusts the declaration and does not independently verify randomization, exposure, exclusions, or analysis population.",
        ),
        RuleSpec(
            "CC304",
            Severity.REVIEW,
            ("claim.type", "claim.text", "evidence.design", "evidence.caveats"),
            "An observational intervention comparison lacks an explicit non-causal caveat.",
            "Caveat detection is text-based and does not prove that downstream language will preserve the intended non-causal interpretation.",
        ),
        RuleSpec(
            "CC305",
            Severity.REVIEW,
            ("claim.type", "claim.text", "evidence.design"),
            "An otherwise eligible causal claim still requires qualified human analytical review.",
            "The rule deliberately does not automate scientific approval; the required review remains outside the harness.",
        ),
    ),
)

_PROFILE_MANIFESTS = {MINIMUM_V0_1.name: MINIMUM_V0_1}


def supported_profiles() -> tuple[str, ...]:
    return tuple(_PROFILE_MANIFESTS)


def get_profile_manifest(name: str) -> ProfileManifest:
    try:
        return _PROFILE_MANIFESTS[name]
    except KeyError as exc:
        supported = ", ".join(supported_profiles())
        raise ValueError(
            f"Unsupported profile {name!r}. Supported profiles: {supported}."
        ) from exc
