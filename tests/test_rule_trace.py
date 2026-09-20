from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest

from claim_contract import build_rule_trace, load_contract, validate_contract
from claim_contract.cli import main
from claim_contract.profiles import get_profile_manifest
from claim_contract.validator import (
    TRACE_NOT_APPLICABLE,
    TRACE_PASS,
    TRACE_TRIGGERED,
)


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "rule-trace-v1.schema.json"
READY = ROOT / "examples" / "descriptive_summary" / "contract.yaml"
REVIEW = ROOT / "examples" / "missing_uncertainty" / "contract.yaml"
BLOCK = ROOT / "examples" / "onboarding_conversion" / "contract.yaml"


def _schema() -> dict:
    payload = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _by_id(trace) -> dict:
    return {rule.rule_id: rule for rule in trace.rules}


def _finding_key(finding) -> tuple[str, str, str, str, str]:
    return (
        finding.rule_id,
        finding.severity.value,
        finding.path,
        finding.message,
        finding.action,
    )


def test_rule_trace_schema_is_valid_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_ready_trace_explains_pass_and_not_applicable_rules() -> None:
    contract = load_contract(READY)
    trace = build_rule_trace(contract)
    payload = trace.to_dict()

    jsonschema.validate(payload, _schema())
    assert trace.verdict == "READY"
    assert payload["scientific_validation"] is False
    assert payload["automatic_interpretation"] is False
    assert payload["summary"]["triggered_count"] == 0
    assert payload["summary"]["finding_count"] == 0

    by_id = _by_id(trace)
    assert by_id["CC001"].status == TRACE_PASS
    assert by_id["CC101"].status == TRACE_PASS
    assert by_id["CC102"].status == TRACE_PASS
    assert by_id["CC201"].status == TRACE_NOT_APPLICABLE
    assert by_id["CC301"].status == TRACE_NOT_APPLICABLE

    manifest = get_profile_manifest("minimum-v0.1")
    assert [rule.rule_id for rule in trace.rules] == [
        rule.rule_id for rule in manifest.rules
    ]


@pytest.mark.parametrize(
    "path",
    sorted((ROOT / "examples").rglob("contract.yaml")),
    ids=lambda path: str(path.relative_to(ROOT / "examples")),
)
def test_trace_triggered_entries_exactly_match_validator_findings(path: Path) -> None:
    contract = load_contract(path)
    report = validate_contract(contract)
    trace = build_rule_trace(contract)

    assert trace.verdict == report.verdict.value

    trace_findings = [
        finding
        for rule in trace.rules
        for finding in rule.findings
    ]
    assert sorted(_finding_key(finding) for finding in trace_findings) == sorted(
        _finding_key(finding) for finding in report.findings
    )

    triggered_ids = {
        rule.rule_id for rule in trace.rules if rule.status == TRACE_TRIGGERED
    }
    report_ids = {finding.rule_id for finding in report.findings}
    assert triggered_ids == report_ids

    for rule in trace.rules:
        if rule.status == TRACE_TRIGGERED:
            assert rule.findings
            assert all(finding.rule_id == rule.rule_id for finding in rule.findings)
        else:
            assert rule.findings == ()


def test_review_trace_distinguishes_applicable_pass_from_trigger() -> None:
    trace = build_rule_trace(load_contract(REVIEW))
    by_id = _by_id(trace)

    assert trace.verdict == "REVIEW"
    assert by_id["CC201"].status == TRACE_PASS
    assert by_id["CC203"].status == TRACE_TRIGGERED
    assert by_id["CC203"].findings[0].path == "evidence.uncertainty"


def test_trace_does_not_mutate_contract() -> None:
    contract = load_contract(BLOCK)
    before = deepcopy(contract)

    build_rule_trace(contract)

    assert contract == before


def test_trace_cli_block_is_successful_inspection_not_gate(capsys) -> None:
    code = main(["trace", str(BLOCK), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    jsonschema.validate(payload, _schema())
    assert payload["type"] == "claim_contract.rule_trace"
    assert payload["verdict"] == "BLOCK"
    assert payload["summary"]["triggered_count"] > 0


def test_trace_cli_text_names_all_three_states(capsys) -> None:
    code = main(["trace", str(REVIEW)])
    output = capsys.readouterr().out

    assert code == 0
    assert "Rule trace:" in output
    assert "TRIGGERED" in output
    assert "PASS" in output
    assert "NOT_APPLICABLE" in output
    assert "PASS does not establish" in output


def test_trace_cli_json_input_error_uses_existing_error_envelope(capsys, tmp_path) -> None:
    missing = tmp_path / "missing.yaml"
    code = main(["trace", str(missing), "--json"])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["type"] == "claim_contract.error"
    assert "Input error:" in payload["message"]
