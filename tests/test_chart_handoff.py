from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import jsonschema

from claim_contract import build_chart_handoff, load_contract
from claim_contract.cli import main
from claim_contract.handoff import handoff_exit_code
from claim_contract.models import Verdict

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "schemas/chart-handoff-v1.schema.json"
READY_CONTRACT = ROOT / "examples/descriptive_summary/contract.yaml"
REVIEW_CONTRACT = ROOT / "examples/missing_uncertainty/contract.yaml"
BLOCK_CONTRACT = ROOT / "examples/onboarding_conversion/contract.yaml"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _walk_keys(value) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            keys.update(_walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_walk_keys(item))
    return keys


def test_chart_handoff_schema_is_valid_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_ready_chart_handoff_is_schema_valid_and_bounded() -> None:
    contract = load_contract(READY_CONTRACT)
    handoff = build_chart_handoff(contract)
    payload = handoff.to_dict()

    jsonschema.validate(payload, _schema())

    assert payload["type"] == "claim_contract.chart_handoff"
    assert payload["schema_version"] == "1.0"
    assert payload["destination"] == {
        "tool": "chart-contract",
        "purpose": "bounded_claim_context",
    }
    assert payload["claim"] == {
        "text": "Median support-ticket resolution time was 18 hours in June 2026.",
        "metric": {
            "name": "median_resolution_hours",
            "unit": "hours",
        },
        "population": "support tickets closed in June 2026",
        "time_window": "2026-06-01/2026-06-30",
    }
    assert payload["evidence_context"] == {
        "provenance_source": "warehouse.support_tickets",
        "caveats": ["Operational summary for the declared population and window only."],
    }
    assert payload["validation"]["verdict"] == "READY"
    assert payload["validation"]["scientific_validation"] is False
    assert payload["validation"]["findings"] == []
    assert payload["contract"]["profile"] == "minimum-v0.1"
    assert payload["contract"]["input_binding"]["algorithm"] == "sha256"
    assert len(payload["contract"]["input_binding"]["contract_sha256"]) == 64

    forbidden = {
        "chart",
        "chart_type",
        "encoding",
        "mark",
        "recommendation",
        "recommended_chart",
        "visualization",
    }
    assert forbidden.isdisjoint(_walk_keys(payload))


def test_handoff_binding_detects_contract_drift() -> None:
    contract = load_contract(READY_CONTRACT)
    handoff = build_chart_handoff(contract)

    assert handoff.matches_contract(contract)

    changed = deepcopy(contract)
    changed["claim"]["time_window"] = "2026-06-01/2026-07-31"
    assert not handoff.matches_contract(changed)


def test_blocked_claim_is_exported_without_laundering() -> None:
    handoff = build_chart_handoff(load_contract(BLOCK_CONTRACT))
    payload = handoff.to_dict()

    jsonschema.validate(payload, _schema())
    assert handoff.report.verdict is Verdict.BLOCK
    assert payload["validation"]["verdict"] == "BLOCK"
    assert any(
        finding["rule_id"] == "CC301"
        for finding in payload["validation"]["findings"]
    )
    assert handoff_exit_code(handoff) == 1


def test_review_handoff_preserves_validation_exit_policy() -> None:
    handoff = build_chart_handoff(load_contract(REVIEW_CONTRACT))

    assert handoff.report.verdict is Verdict.REVIEW
    assert handoff_exit_code(handoff) == 0
    assert handoff_exit_code(handoff, warnings_as_errors=True) == 1


def test_missing_transfer_field_stays_missing_and_blocked() -> None:
    contract = load_contract(READY_CONTRACT)
    del contract["claim"]["population"]

    handoff = build_chart_handoff(contract)
    payload = handoff.to_dict()

    jsonschema.validate(payload, _schema())
    assert payload["claim"]["population"] is None
    assert payload["validation"]["verdict"] == "BLOCK"
    assert any(
        finding["rule_id"] == "CC001" and finding["path"] == "claim.population"
        for finding in payload["validation"]["findings"]
    )


def test_cli_emits_json_handoff_and_block_exit(capsys) -> None:
    code = main(["handoff", "chart", str(BLOCK_CONTRACT)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["type"] == "claim_contract.chart_handoff"
    assert payload["validation"]["verdict"] == "BLOCK"
    jsonschema.validate(payload, _schema())


def test_cli_review_can_fail_closed_without_changing_artifact(capsys) -> None:
    default_code = main(["handoff", "chart", str(REVIEW_CONTRACT)])
    default_payload = json.loads(capsys.readouterr().out)

    strict_code = main(
        ["handoff", "chart", str(REVIEW_CONTRACT), "--warnings-as-errors"]
    )
    strict_payload = json.loads(capsys.readouterr().out)

    assert default_code == 0
    assert strict_code == 1
    assert default_payload == strict_payload
    assert default_payload["validation"]["verdict"] == "REVIEW"


def test_cli_handoff_input_error_stays_machine_readable(capsys, tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    code = main(["handoff", "chart", str(missing)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["type"] == "claim_contract.error"
    assert payload["scientific_validation"] is False
