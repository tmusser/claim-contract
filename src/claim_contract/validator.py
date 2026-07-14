from __future__ import annotations

import re
from typing import Any, Iterable

from .models import Finding, Report, Severity, Verdict

_SUPPORTED_PROFILE = "minimum-v0.1"
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
    rule_id: str,
    severity: Severity,
    path: str,
    message: str,
    action: str,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,
        path=path,
        message=message,
        action=action,
    )


def validate_contract(contract: dict[str, Any]) -> Report:
    profile = str(contract.get("profile", _SUPPORTED_PROFILE))
    if profile != _SUPPORTED_PROFILE:
        raise ValueError(
            f"Unsupported profile '{profile}'. Supported profiles: {_SUPPORTED_PROFILE}."
        )

    findings: list[Finding] = []
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
                    "CC001",
                    Severity.BLOCK,
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
                "CC001",
                Severity.BLOCK,
                "evidence.sample_size",
                "Sample size must be a positive number.",
                "Provide the analyzed sample size as a positive numeric value.",
            )
        )

    if claim_type and claim_type not in {"descriptive", "comparison", "causal"}:
        findings.append(
            _finding(
                "CC001",
                Severity.BLOCK,
                "claim.type",
                f"Unsupported claim type '{claim_type}'.",
                "Use one of: descriptive, comparison, causal.",
            )
        )

    if _get(contract, "evidence.checks.metric_definition_locked") is not True:
        findings.append(
            _finding(
                "CC101",
                Severity.REVIEW,
                "evidence.checks.metric_definition_locked",
                "The metric definition was not declared locked before interpretation.",
                "Confirm the numerator, denominator, exclusions, aggregation, and version.",
            )
        )

    if _get(contract, "evidence.checks.missingness_assessed") is not True:
        findings.append(
            _finding(
                "CC102",
                Severity.REVIEW,
                "evidence.checks.missingness_assessed",
                "Missingness was not declared assessed.",
                "Assess missingness and document how it affects the declared metric and population.",
            )
        )

    comparison_required = claim_type in {"comparison", "causal"} or causal_language
    baseline_group = _get(contract, "claim.comparison.baseline")
    comparison_group = _get(contract, "claim.comparison.comparison")
    if comparison_required and (_is_blank(baseline_group) or _is_blank(comparison_group)):
        findings.append(
            _finding(
                "CC201",
                Severity.BLOCK,
                "claim.comparison",
                "Comparison or causal claims require explicit baseline and comparison groups.",
                "Declare both groups, periods, or conditions being compared.",
            )
        )

    effect_scale = str(_get(contract, "evidence.estimate.scale", "")).lower()
    relative_claim = effect_scale in {"relative", "percent", "percentage"} or _matches_any(
        claim_text, _RELATIVE_PATTERNS
    )
    if comparison_required and relative_claim and _is_blank(
        _get(contract, "evidence.estimate.baseline_value")
    ):
        findings.append(
            _finding(
                "CC202",
                Severity.BLOCK,
                "evidence.estimate.baseline_value",
                "A relative or percentage comparison lacks the baseline value needed for interpretation.",
                "Provide the baseline value or rewrite the claim as an absolute comparison.",
            )
        )

    if comparison_required and _get(contract, "evidence.estimate.value") is not None:
        if _is_blank(_get(contract, "evidence.uncertainty")):
            findings.append(
                _finding(
                    "CC203",
                    Severity.REVIEW,
                    "evidence.uncertainty",
                    "The estimate has no declared uncertainty information.",
                    "Provide an interval, standard error, resampling summary, or explain why uncertainty is out of scope.",
                )
            )

    if design == "observational_before_after" and (
        _get(contract, "evidence.checks.composition_stability_assessed") is not True
    ):
        findings.append(
            _finding(
                "CC204",
                Severity.REVIEW,
                "evidence.checks.composition_stability_assessed",
                "Composition stability was not assessed for an observational before/after comparison.",
                "Check whether population or segment mix changed across the comparison window.",
            )
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
                    "CC205",
                    Severity.REVIEW,
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
                    "CC205",
                    Severity.REVIEW,
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
                    "CC205",
                    Severity.REVIEW,
                    "evidence.multiplicity",
                    "Multiple comparisons were declared without an adjustment strategy or rationale.",
                    "Declare an adjustment method or explain why no adjustment was used.",
                )
            )

    magnitude_language = _matches_any(claim_text, _MAGNITUDE_PATTERNS)
    if magnitude_language and (
        _is_blank(_get(contract, "evidence.estimate.value"))
        or _is_blank(_get(contract, "evidence.estimate.scale"))
    ):
        findings.append(
            _finding(
                "CC206",
                Severity.BLOCK,
                "evidence.estimate",
                "Magnitude language lacks a numeric effect estimate on a declared scale.",
                "Report the estimate value and scale, or remove qualitative magnitude language.",
            )
        )

    if causal_language and design not in _CAUSAL_DESIGNS:
        findings.append(
            _finding(
                "CC301",
                Severity.BLOCK,
                "claim.text",
                f"Causal language is not eligible under design '{design or 'undeclared'}'.",
                "Use non-causal wording or provide an eligible design and its required diagnostics.",
            )
        )

    if causal_language and design == "quasi_experiment":
        if _get(contract, "evidence.checks.identifying_assumptions_documented") is not True:
            findings.append(
                _finding(
                    "CC302",
                    Severity.BLOCK,
                    "evidence.checks.identifying_assumptions_documented",
                    "The quasi-experimental claim lacks declared identifying assumptions.",
                    "Document the design-specific identifying assumptions and diagnostics.",
                )
            )

    if causal_language and design == "randomized_experiment":
        if _get(contract, "evidence.checks.treatment_assignment_validated") is not True:
            findings.append(
                _finding(
                    "CC303",
                    Severity.BLOCK,
                    "evidence.checks.treatment_assignment_validated",
                    "Randomized assignment was not declared validated.",
                    "Verify assignment integrity, exposure, exclusions, and analysis population.",
                )
            )

    if causal_language and design in _CAUSAL_DESIGNS:
        findings.append(
            _finding(
                "CC305",
                Severity.REVIEW,
                "claim.type",
                "Causal claims require qualified human analytical review under minimum-v0.1.",
                "Have a qualified reviewer inspect the design, diagnostics, assumptions, and execution evidence.",
            )
        )

    caveats = _get(contract, "evidence.caveats", [])
    has_noncausal_caveat = isinstance(caveats, list) and any(
        any(token in str(item).lower() for token in ("not causal", "cannot attribute", "observational"))
        for item in caveats
    )
    if design == "observational_before_after" and comparison_required and not has_noncausal_caveat:
        findings.append(
            _finding(
                "CC304",
                Severity.REVIEW,
                "evidence.caveats",
                "The observational intervention comparison lacks an explicit non-causal caveat.",
                "State that timing or association does not establish attribution.",
            )
        )

    severity_values = {finding.severity for finding in findings}
    if Severity.BLOCK in severity_values:
        verdict = Verdict.BLOCK
    elif Severity.REVIEW in severity_values:
        verdict = Verdict.REVIEW
    else:
        verdict = Verdict.READY

    return Report(
        verdict=verdict,
        profile=profile,
        claim_text=claim_text,
        findings=findings,
    )
