from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .binding import build_contract_binding
from .models import Finding, Report, Severity, Verdict
from .profiles import DEFAULT_PROFILE, ProfileManifest, get_profile_manifest

_CAUSAL_DESIGNS = {"randomized_experiment", "quasi_experiment"}
_CAUSAL_PATTERNS = [
    r"\bcaus(?:e|ed|es|al)\b",
    r"\bdrove\b",
    r"\bdrives\b",
    r"\bled to\b",
    r"\bresulted in\b",
    r"\battributable to\b",
    r"\bdue to\b",
    r"\bbecause of\b",
    r"\b(?:redesign|treatment|intervention|policy|campaign|program|feature|launch)\b.{0,60}\b(?:improved|increased|decreased|reduced)\b",
]
_RELATIVE_PATTERNS = [
    r"%",
    r"\bpercent(?:age)?\b",
    r"\brelative\b",
    r"\bhigher\b",
    r"\blower\b",
    r"\bincreas(?:e|ed)\b",
    r"\bdecreas(?:e|ed)\b",
]
_MAGNITUDE_PATTERNS = [
    r"\b(?:large|substantial|material|meaningful|major|dramatic|sizeable|sizable|small|modest|negligible|trivial)\b",
]

TRACE_TRIGGERED = "TRIGGERED"
TRACE_PASS = "PASS"
TRACE_NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    status: str
    reason: str
    findings: tuple[Finding, ...]


def _get(data: dict[str, Any], path: str, default: Any = None) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def _is_blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _matches_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _finding(
    manifest: ProfileManifest,
    rule_id: str,
    path: str,
    message: str,
    action: str,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=manifest.rule(rule_id).severity,
        path=path,
        message=message,
        action=action,
    )


def _rule_evaluation(
    rule_id: str,
    *,
    applicable: bool,
    findings: list[Finding],
    pass_reason: str,
    not_applicable_reason: str,
) -> RuleEvaluation:
    rule_findings = tuple(finding for finding in findings if finding.rule_id == rule_id)
    if rule_findings:
        return RuleEvaluation(
            rule_id=rule_id,
            status=TRACE_TRIGGERED,
            reason=f"Rule emitted {len(rule_findings)} finding(s).",
            findings=rule_findings,
        )
    if applicable:
        return RuleEvaluation(
            rule_id=rule_id,
            status=TRACE_PASS,
            reason=pass_reason,
            findings=(),
        )
    return RuleEvaluation(
        rule_id=rule_id,
        status=TRACE_NOT_APPLICABLE,
        reason=not_applicable_reason,
        findings=(),
    )


def _evaluate_contract(
    contract: dict[str, Any],
) -> tuple[Report, tuple[RuleEvaluation, ...]]:
    profile = str(contract.get("profile", DEFAULT_PROFILE))
    manifest = get_profile_manifest(profile)

    findings: list[Finding] = []
    evaluations: dict[str, RuleEvaluation] = {}
    claim_text = str(_get(contract, "claim.text", "") or "")

    required = {
        "claim.text": "Provide the exact proposed claim.",
        "claim.type": "Declare descriptive, comparison, or causal.",
        "claim.population": "Declare the population covered by the claim.",
        "claim.time_window": "Declare the time window covered by the claim.",
        "claim.metric.name": "Declare the metric name.",
        "claim.metric.unit": "Declare the metric unit.",
        "claim.metric.definition": "Declare the metric definition and denominator when relevant.",
        "evidence.design": "Declare the analytical design.",
        "evidence.sample_size": "Declare the analyzed sample size.",
        "evidence.provenance.source": "Declare the source or provenance identifier.",
        "evidence.checks": "Declare the minimum check fields explicitly.",
    }
    for path, action in required.items():
        if _is_blank(_get(contract, path)):
            findings.append(
                _finding(
                    manifest,
                    "CC001",
                    path,
                    f"Required field '{path}' is missing.",
                    action,
                )
            )

    claim_type = str(_get(contract, "claim.type", "")).lower()
    design = str(_get(contract, "evidence.design", "")).lower()
    causal_language = claim_type == "causal" or _matches_any(claim_text, _CAUSAL_PATTERNS)

    sample_size = _get(contract, "evidence.sample_size")
    if sample_size is not None and (
        isinstance(sample_size, bool)
        or not isinstance(sample_size, (int, float))
        or sample_size <= 0
    ):
        findings.append(
            _finding(
                manifest,
                "CC001",
                "evidence.sample_size",
                "Sample size must be a positive number.",
                "Provide the analyzed sample size as a positive numeric value.",
            )
        )

    if claim_type and claim_type not in {"descriptive", "comparison", "causal"}:
        findings.append(
            _finding(
                manifest,
                "CC001",
                "claim.type",
                f"Unsupported claim type '{claim_type}'.",
                "Use one of: descriptive, comparison, causal.",
            )
        )

    evaluations["CC001"] = _rule_evaluation(
        "CC001",
        applicable=True,
        findings=findings,
        pass_reason="All required fields and basic supported values passed the implemented checks.",
        not_applicable_reason="CC001 is always applicable.",
    )

    if _get(contract, "evidence.checks.metric_definition_locked") is not True:
        findings.append(
            _finding(
                manifest,
                "CC101",
                "evidence.checks.metric_definition_locked",
                "The metric definition was not declared locked before interpretation.",
                "Confirm the numerator, denominator, exclusions, aggregation, and version.",
            )
        )
    evaluations["CC101"] = _rule_evaluation(
        "CC101",
        applicable=True,
        findings=findings,
        pass_reason="The contract declares metric_definition_locked as true.",
        not_applicable_reason="CC101 is always applicable.",
    )

    if _get(contract, "evidence.checks.missingness_assessed") is not True:
        findings.append(
            _finding(
                manifest,
                "CC102",
                "evidence.checks.missingness_assessed",
                "Missingness was not declared assessed.",
                "Assess missingness and document how it affects the declared metric and population.",
            )
        )
    evaluations["CC102"] = _rule_evaluation(
        "CC102",
        applicable=True,
        findings=findings,
        pass_reason="The contract declares missingness_assessed as true.",
        not_applicable_reason="CC102 is always applicable.",
    )

    comparison_required = claim_type in {"comparison", "causal"} or causal_language
    baseline_group = _get(contract, "claim.comparison.baseline")
    comparison_group = _get(contract, "claim.comparison.comparison")
    if comparison_required and (_is_blank(baseline_group) or _is_blank(comparison_group)):
        findings.append(
            _finding(
                manifest,
                "CC201",
                "claim.comparison",
                "Comparison or causal claims require explicit baseline and comparison groups.",
                "Declare both groups, periods, or conditions being compared.",
            )
        )
    evaluations["CC201"] = _rule_evaluation(
        "CC201",
        applicable=comparison_required,
        findings=findings,
        pass_reason="A comparison/causal requirement was detected and both comparison groups are declared.",
        not_applicable_reason="No comparison/causal requirement was detected from claim type or causal-language matching.",
    )

    effect_scale = str(_get(contract, "evidence.estimate.scale", "")).lower()
    relative_claim = effect_scale in {"relative", "percent", "percentage"} or _matches_any(
        claim_text, _RELATIVE_PATTERNS
    )
    cc202_applicable = comparison_required and relative_claim
    if cc202_applicable and _is_blank(_get(contract, "evidence.estimate.baseline_value")):
        findings.append(
            _finding(
                manifest,
                "CC202",
                "evidence.estimate.baseline_value",
                "A relative or percentage comparison lacks the baseline value needed for interpretation.",
                "Provide the baseline value or rewrite the claim as an absolute comparison.",
            )
        )
    evaluations["CC202"] = _rule_evaluation(
        "CC202",
        applicable=cc202_applicable,
        findings=findings,
        pass_reason="A relative/percentage comparison was detected and a baseline value is declared.",
        not_applicable_reason=(
            "The rule requires both a comparison/causal context and relative/percentage language or scale."
        ),
    )

    estimate_value = _get(contract, "evidence.estimate.value")
    cc203_applicable = comparison_required and estimate_value is not None
    if cc203_applicable and _is_blank(_get(contract, "evidence.uncertainty")):
        findings.append(
            _finding(
                manifest,
                "CC203",
                "evidence.uncertainty",
                "The estimate has no declared uncertainty information.",
                "Provide an interval, standard error, resampling summary, or explain why uncertainty is out of scope.",
            )
        )
    evaluations["CC203"] = _rule_evaluation(
        "CC203",
        applicable=cc203_applicable,
        findings=findings,
        pass_reason="A comparative/causal estimate is present and uncertainty information is declared.",
        not_applicable_reason="The rule requires a comparison/causal context with a declared estimate value.",
    )

    cc204_applicable = design == "observational_before_after"
    if cc204_applicable and (
        _get(contract, "evidence.checks.composition_stability_assessed") is not True
    ):
        findings.append(
            _finding(
                manifest,
                "CC204",
                "evidence.checks.composition_stability_assessed",
                "Composition stability was not assessed for an observational before/after comparison.",
                "Check whether population or segment mix changed across the comparison window.",
            )
        )
    evaluations["CC204"] = _rule_evaluation(
        "CC204",
        applicable=cc204_applicable,
        findings=findings,
        pass_reason="The observational before/after design declares composition stability assessed.",
        not_applicable_reason="The declared design is not observational_before_after.",
    )

    if comparison_required:
        multiplicity_assessed = _get(
            contract, "evidence.checks.multiple_comparisons_assessed"
        )
        multiplicity = _get(contract, "evidence.multiplicity", {})
        comparisons = (
            multiplicity.get("comparisons") if isinstance(multiplicity, dict) else None
        )
        adjustment = (
            multiplicity.get("adjustment") if isinstance(multiplicity, dict) else None
        )
        rationale = (
            multiplicity.get("rationale") if isinstance(multiplicity, dict) else None
        )

        if multiplicity_assessed is not True:
            findings.append(
                _finding(
                    manifest,
                    "CC205",
                    "evidence.checks.multiple_comparisons_assessed",
                    "Multiple-comparison risk was not declared assessed.",
                    "Declare whether the claim was selected from multiple tests, outcomes, segments, or variants.",
                )
            )
        elif comparisons is not None and (
            isinstance(comparisons, bool)
            or not isinstance(comparisons, (int, float))
            or comparisons < 1
        ):
            findings.append(
                _finding(
                    manifest,
                    "CC205",
                    "evidence.multiplicity.comparisons",
                    "The declared comparison count is not a positive number.",
                    "Provide the number of comparisons considered or omit the field when unknown.",
                )
            )
        elif (
            comparisons is not None
            and comparisons > 1
            and _is_blank(adjustment)
            and _is_blank(rationale)
        ):
            findings.append(
                _finding(
                    manifest,
                    "CC205",
                    "evidence.multiplicity",
                    "Multiple comparisons were declared without an adjustment strategy or rationale.",
                    "Declare an adjustment method or explain why no adjustment was used.",
                )
            )
    evaluations["CC205"] = _rule_evaluation(
        "CC205",
        applicable=comparison_required,
        findings=findings,
        pass_reason="Comparison multiplicity declarations passed the implemented checks.",
        not_applicable_reason="No comparison/causal requirement was detected.",
    )

    magnitude_language = _matches_any(claim_text, _MAGNITUDE_PATTERNS)
    if magnitude_language and (
        _is_blank(_get(contract, "evidence.estimate.value"))
        or _is_blank(_get(contract, "evidence.estimate.scale"))
    ):
        findings.append(
            _finding(
                manifest,
                "CC206",
                "evidence.estimate",
                "Magnitude language lacks a numeric effect estimate on a declared scale.",
                "Report the estimate value and scale, or remove qualitative magnitude language.",
            )
        )
    evaluations["CC206"] = _rule_evaluation(
        "CC206",
        applicable=magnitude_language,
        findings=findings,
        pass_reason="Qualitative magnitude language was detected with a numeric estimate and declared scale.",
        not_applicable_reason="No configured qualitative magnitude-language pattern was detected.",
    )

    if causal_language and design not in _CAUSAL_DESIGNS:
        findings.append(
            _finding(
                manifest,
                "CC301",
                "claim.text",
                f"Causal language is not eligible under design '{design or 'undeclared'}'.",
                "Use non-causal wording or provide an eligible design and its required diagnostics.",
            )
        )
    evaluations["CC301"] = _rule_evaluation(
        "CC301",
        applicable=causal_language,
        findings=findings,
        pass_reason="Causal language was detected and the declared design is eligible in this profile.",
        not_applicable_reason="No causal claim type or configured causal-language pattern was detected.",
    )

    cc302_applicable = causal_language and design == "quasi_experiment"
    if cc302_applicable:
        if _get(contract, "evidence.checks.identifying_assumptions_documented") is not True:
            findings.append(
                _finding(
                    manifest,
                    "CC302",
                    "evidence.checks.identifying_assumptions_documented",
                    "The quasi-experimental claim lacks declared identifying assumptions.",
                    "Document the design-specific identifying assumptions and diagnostics.",
                )
            )
    evaluations["CC302"] = _rule_evaluation(
        "CC302",
        applicable=cc302_applicable,
        findings=findings,
        pass_reason="The quasi-experimental causal claim declares identifying assumptions documented.",
        not_applicable_reason="The rule requires causal language with design quasi_experiment.",
    )

    cc303_applicable = causal_language and design == "randomized_experiment"
    if cc303_applicable:
        if _get(contract, "evidence.checks.treatment_assignment_validated") is not True:
            findings.append(
                _finding(
                    manifest,
                    "CC303",
                    "evidence.checks.treatment_assignment_validated",
                    "Randomized assignment was not declared validated.",
                    "Verify assignment integrity, exposure, exclusions, and analysis population.",
                )
            )
    evaluations["CC303"] = _rule_evaluation(
        "CC303",
        applicable=cc303_applicable,
        findings=findings,
        pass_reason="The randomized causal claim declares treatment assignment validated.",
        not_applicable_reason="The rule requires causal language with design randomized_experiment.",
    )

    cc305_applicable = causal_language and design in _CAUSAL_DESIGNS
    if cc305_applicable:
        findings.append(
            _finding(
                manifest,
                "CC305",
                "claim.type",
                "Causal claims require qualified human analytical review under minimum-v0.1.",
                "Have a qualified reviewer inspect the design, diagnostics, assumptions, and execution evidence.",
            )
        )
    evaluations["CC305"] = _rule_evaluation(
        "CC305",
        applicable=cc305_applicable,
        findings=findings,
        pass_reason="Eligible causal claims always trigger qualified human review under minimum-v0.1.",
        not_applicable_reason="The rule requires causal language paired with an eligible causal design.",
    )

    caveats = _get(contract, "evidence.caveats", [])
    has_noncausal_caveat = isinstance(caveats, list) and any(
        any(
            token in str(item).lower()
            for token in ("not causal", "cannot attribute", "observational")
        )
        for item in caveats
    )
    cc304_applicable = design == "observational_before_after" and comparison_required
    if cc304_applicable and not has_noncausal_caveat:
        findings.append(
            _finding(
                manifest,
                "CC304",
                "evidence.caveats",
                "The observational intervention comparison lacks an explicit non-causal caveat.",
                "State that timing or association does not establish attribution.",
            )
        )
    evaluations["CC304"] = _rule_evaluation(
        "CC304",
        applicable=cc304_applicable,
        findings=findings,
        pass_reason="The observational intervention comparison includes a configured explicit non-causal caveat.",
        not_applicable_reason="The rule requires an observational_before_after design in a comparison/causal context.",
    )

    severity_values = {finding.severity for finding in findings}
    if Severity.BLOCK in severity_values:
        verdict = Verdict.BLOCK
    elif Severity.REVIEW in severity_values:
        verdict = Verdict.REVIEW
    else:
        verdict = Verdict.READY

    contract_version_value = contract.get("version")
    contract_version = (
        None if contract_version_value is None else str(contract_version_value)
    )

    report = Report(
        verdict=verdict,
        profile=profile,
        claim_text=claim_text,
        contract_version=contract_version,
        input_binding=build_contract_binding(contract),
        findings=findings,
    )
    ordered_evaluations = tuple(
        evaluations[rule.rule_id]
        for rule in manifest.rules
    )
    return report, ordered_evaluations


def validate_contract(contract: dict[str, Any]) -> Report:
    return _evaluate_contract(contract)[0]


def validate_contract_with_trace(
    contract: dict[str, Any],
) -> tuple[Report, tuple[RuleEvaluation, ...]]:
    return _evaluate_contract(contract)
