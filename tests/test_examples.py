from __future__ import annotations

from pathlib import Path

import pytest

from claim_contract import load_contract, validate_contract

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    ("fixture", "expected_verdict", "expected_rule_ids"),
    [
        ("descriptive_summary", "READY", set()),
        ("missing_uncertainty", "REVIEW", {"CC203"}),
        (
            "onboarding_conversion",
            "BLOCK",
            {"CC203", "CC204", "CC301", "CC304"},
        ),
    ],
)
def test_example_verdicts_are_stable(
    fixture: str,
    expected_verdict: str,
    expected_rule_ids: set[str],
) -> None:
    contract = load_contract(ROOT / "examples" / fixture / "contract.yaml")
    report = validate_contract(contract)

    assert report.verdict.value == expected_verdict
    assert {finding.rule_id for finding in report.findings} == expected_rule_ids
    assert report.scientific_validation is False
    assert "not scientific validation" in report.scope_notice.lower()
    assert report.not_evaluated
