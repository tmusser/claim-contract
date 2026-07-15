from __future__ import annotations

from pathlib import Path

import pytest

from claim_contract import load_contract, validate_contract

ROOT = Path(__file__).parents[1]
ADVERSARIAL = ROOT / "examples" / "adversarial"


@pytest.mark.parametrize(
    ("fixture", "expected_verdict", "expected_rule_ids"),
    [
        ("false_confidence_ready", "READY", set()),
        ("undeclared_assumptions", "BLOCK", {"CC302", "CC305"}),
        ("agent_misuse", "READY", set()),
    ],
)
def test_adversarial_contract_results_are_stable(
    fixture: str,
    expected_verdict: str,
    expected_rule_ids: set[str],
) -> None:
    contract = load_contract(ADVERSARIAL / fixture / "contract.yaml")
    report = validate_contract(contract)

    assert report.verdict.value == expected_verdict
    assert {finding.rule_id for finding in report.findings} == expected_rule_ids
    assert report.scientific_validation is False
    assert "not scientific validation" in report.scope_notice.lower()
    assert report.not_evaluated


def test_false_confidence_ready_keeps_unverified_caveat_visible() -> None:
    contract = load_contract(ADVERSARIAL / "false_confidence_ready" / "contract.yaml")
    report = validate_contract(contract)

    assert report.verdict.value == "READY"
    assert contract["evidence"]["provenance"]["source"] == "agent_supplied.unverified_export"
    assert any(
        "not independently verified" in caveat.lower()
        for caveat in contract["evidence"]["caveats"]
    )


def test_agent_misuse_fixture_contrasts_unsafe_and_safe_summaries() -> None:
    fixture = ADVERSARIAL / "agent_misuse"
    unsafe = (fixture / "unsafe_summary.md").read_text(encoding="utf-8").lower()
    safe = (fixture / "safe_summary.md").read_text(encoding="utf-8").lower()

    assert "scientifically valid" in unsafe
    assert "safe to publish" in unsafe
    assert "declared minimum contract is ready" not in unsafe

    assert "declared minimum contract is ready" in safe
    assert "does not validate the underlying science or analysis" in safe
    assert "human review" in safe
