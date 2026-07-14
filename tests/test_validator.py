from __future__ import annotations

from copy import deepcopy

from claim_contract.models import Verdict
from claim_contract.validator import validate_contract


def ready_contract() -> dict:
    return {
        "version": "0.1",
        "profile": "minimum-v0.1",
        "claim": {
            "text": "Seven-day activation was 27% among eligible new users in Q2.",
            "type": "descriptive",
            "population": "eligible new users",
            "time_window": "2026-Q2",
            "metric": {
                "name": "seven_day_activation_rate",
                "unit": "proportion",
                "definition": "activated users / eligible users",
            },
        },
        "evidence": {
            "design": "descriptive_summary",
            "sample_size": 1000,
            "estimate": {"value": 0.27, "scale": "absolute"},
            "uncertainty": {"method": "binomial", "lower": 0.24, "upper": 0.30},
            "provenance": {"source": "warehouse.events"},
            "checks": {
                "metric_definition_locked": True,
                "missingness_assessed": True,
                "composition_stability_assessed": True,
                "treatment_assignment_validated": False,
                "identifying_assumptions_documented": False,
                "multiple_comparisons_assessed": True,
            },
            "caveats": ["Descriptive result only."],
        },
    }


def rule_ids(report) -> set[str]:
    return {finding.rule_id for finding in report.findings}


def test_ready_only_means_no_rules_fired() -> None:
    report = validate_contract(ready_contract())
    assert report.verdict is Verdict.READY
    assert "not scientific validation" in report.scope_notice.lower()
    assert report.not_evaluated


def test_missing_required_field_blocks() -> None:
    contract = ready_contract()
    del contract["claim"]["population"]
    report = validate_contract(contract)
    assert report.verdict is Verdict.BLOCK
    assert "CC001" in rule_ids(report)


def test_causal_language_with_observational_design_blocks() -> None:
    contract = ready_contract()
    contract["claim"].update(
        {
            "text": "The launch caused activation to increase.",
            "type": "causal",
            "comparison": {"baseline": "pre", "comparison": "post"},
        }
    )
    contract["evidence"]["design"] = "observational_before_after"
    contract["evidence"]["estimate"] = {
        "value": 0.08,
        "scale": "relative",
        "baseline_value": 0.25,
    }
    contract["evidence"]["checks"]["composition_stability_assessed"] = False
    contract["evidence"]["caveats"] = []
    report = validate_contract(contract)
    assert report.verdict is Verdict.BLOCK
    assert {"CC301", "CC204", "CC304"}.issubset(rule_ids(report))


def test_relative_comparison_requires_baseline_value() -> None:
    contract = ready_contract()
    contract["claim"].update(
        {
            "text": "Activation was 8% higher post-launch.",
            "type": "comparison",
            "comparison": {"baseline": "pre", "comparison": "post"},
        }
    )
    contract["evidence"]["design"] = "observational_comparison"
    contract["evidence"]["estimate"] = {"value": 0.08, "scale": "relative"}
    report = validate_contract(contract)
    assert report.verdict is Verdict.BLOCK
    assert "CC202" in rule_ids(report)


def test_missing_uncertainty_reviews() -> None:
    contract = ready_contract()
    contract["claim"].update(
        {
            "text": "Activation differed between A and B.",
            "type": "comparison",
            "comparison": {"baseline": "A", "comparison": "B"},
        }
    )
    contract["evidence"]["design"] = "observational_comparison"
    contract["evidence"]["uncertainty"] = None
    report = validate_contract(contract)
    assert report.verdict is Verdict.REVIEW
    assert "CC203" in rule_ids(report)


def test_quasi_experiment_requires_assumptions() -> None:
    contract = ready_contract()
    contract["claim"].update(
        {
            "text": "The policy caused retention to improve.",
            "type": "causal",
            "comparison": {"baseline": "control", "comparison": "treated"},
        }
    )
    contract["evidence"]["design"] = "quasi_experiment"
    contract["evidence"]["checks"]["identifying_assumptions_documented"] = False
    report = validate_contract(contract)
    assert report.verdict is Verdict.BLOCK
    assert "CC302" in rule_ids(report)


def test_randomized_claim_requires_assignment_validation() -> None:
    contract = ready_contract()
    contract["claim"].update(
        {
            "text": "The treatment caused conversion to improve.",
            "type": "causal",
            "comparison": {"baseline": "control", "comparison": "treatment"},
        }
    )
    contract["evidence"]["design"] = "randomized_experiment"
    contract["evidence"]["checks"]["treatment_assignment_validated"] = False
    report = validate_contract(contract)
    assert report.verdict is Verdict.BLOCK
    assert "CC303" in rule_ids(report)


def test_causal_language_cannot_be_laundered_as_comparison() -> None:
    contract = ready_contract()
    contract["claim"].update(
        {
            "text": "The onboarding redesign improved activation.",
            "type": "comparison",
            "comparison": {"baseline": "control", "comparison": "treatment"},
        }
    )
    contract["evidence"]["design"] = "randomized_experiment"
    contract["evidence"]["checks"]["treatment_assignment_validated"] = True
    report = validate_contract(contract)
    assert report.verdict is Verdict.REVIEW
    assert "CC305" in rule_ids(report)


def test_noncausal_use_of_improved_does_not_always_block() -> None:
    contract = ready_contract()
    contract["claim"]["text"] = "Activation improved from April to June."
    report = validate_contract(contract)
    assert report.verdict is Verdict.READY


def test_nonpositive_sample_size_blocks() -> None:
    contract = ready_contract()
    contract["evidence"]["sample_size"] = 0
    report = validate_contract(contract)
    assert report.verdict is Verdict.BLOCK
    assert "CC001" in rule_ids(report)


def test_metric_and_missingness_checks_review() -> None:
    contract = ready_contract()
    contract["evidence"]["checks"]["metric_definition_locked"] = False
    contract["evidence"]["checks"]["missingness_assessed"] = False
    report = validate_contract(contract)
    assert report.verdict is Verdict.REVIEW
    assert {"CC101", "CC102"}.issubset(rule_ids(report))


def test_eligible_causal_claim_still_requires_human_review() -> None:
    contract = ready_contract()
    contract["claim"].update(
        {
            "text": "The randomized treatment caused conversion to improve.",
            "type": "causal",
            "comparison": {"baseline": "control", "comparison": "treatment"},
        }
    )
    contract["evidence"]["design"] = "randomized_experiment"
    contract["evidence"]["checks"]["treatment_assignment_validated"] = True
    report = validate_contract(contract)
    assert report.verdict is Verdict.REVIEW
    assert "CC305" in rule_ids(report)


def test_input_is_not_mutated() -> None:
    contract = ready_contract()
    before = deepcopy(contract)
    validate_contract(contract)
    assert contract == before


def test_unsupported_profile_errors() -> None:
    contract = ready_contract()
    contract["profile"] = "future-profile"
    try:
        validate_contract(contract)
    except ValueError as exc:
        assert "Unsupported profile" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def _comparison_contract() -> dict:
    contract = ready_contract()
    contract["claim"].update(
        {
            "text": "Activation differed between cohort A and cohort B.",
            "type": "comparison",
            "comparison": {"baseline": "cohort_a", "comparison": "cohort_b"},
        }
    )
    contract["evidence"]["design"] = "observational_comparison"
    contract["evidence"]["estimate"] = {"value": 0.02, "scale": "absolute"}
    return contract


def test_comparison_requires_multiple_comparisons_assessment() -> None:
    contract = _comparison_contract()
    contract["evidence"]["checks"]["multiple_comparisons_assessed"] = False
    report = validate_contract(contract)
    assert report.verdict is Verdict.REVIEW
    assert "CC205" in rule_ids(report)


def test_declared_multiple_comparisons_need_handling() -> None:
    contract = _comparison_contract()
    contract["evidence"]["multiplicity"] = {"comparisons": 12}
    report = validate_contract(contract)
    assert report.verdict is Verdict.REVIEW
    assert "CC205" in rule_ids(report)


def test_multiple_comparisons_can_use_explicit_rationale() -> None:
    contract = _comparison_contract()
    contract["evidence"]["multiplicity"] = {
        "comparisons": 12,
        "adjustment": None,
        "rationale": "Exploratory analysis; no confirmatory error-rate claim is made.",
    }
    report = validate_contract(contract)
    assert report.verdict is Verdict.READY
    assert "CC205" not in rule_ids(report)


def test_magnitude_claim_requires_effect_estimate() -> None:
    contract = _comparison_contract()
    contract["claim"]["text"] = "Activation showed a substantial difference between cohorts."
    contract["evidence"]["estimate"] = {}
    report = validate_contract(contract)
    assert report.verdict is Verdict.BLOCK
    assert "CC206" in rule_ids(report)


def test_magnitude_claim_with_estimate_is_eligible() -> None:
    contract = _comparison_contract()
    contract["claim"]["text"] = (
        "Activation showed a substantial 0.02 absolute difference between cohorts."
    )
    report = validate_contract(contract)
    assert report.verdict is Verdict.READY
    assert "CC206" not in rule_ids(report)
