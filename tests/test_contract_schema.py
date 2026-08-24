from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest
import yaml

from claim_contract import load_contract, validate_contract
from claim_contract.cli import main
from claim_contract.models import Verdict

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "schemas/contract-minimum-v0.1.schema.json"
READY_CONTRACT = ROOT / "examples/descriptive_summary/contract.yaml"
BLOCK_CONTRACT = ROOT / "examples/onboarding_conversion/contract.yaml"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _rule_ids(report) -> set[str]:
    return {finding.rule_id for finding in report.findings}


def test_contract_schema_is_valid_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema())


@pytest.mark.parametrize(
    "contract_path",
    sorted((ROOT / "examples").rglob("contract.yaml")),
    ids=lambda path: str(path.relative_to(ROOT / "examples")),
)
def test_every_shipped_contract_matches_minimum_v0_1_schema(
    contract_path: Path,
) -> None:
    jsonschema.validate(load_contract(contract_path), _schema())


def test_schema_rejects_missing_unconditional_required_field() -> None:
    contract = load_contract(READY_CONTRACT)
    del contract["claim"]["population"]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(contract, _schema())


def test_normal_validate_still_emits_cc001_for_schema_missing_field(
    tmp_path: Path,
    capsys,
) -> None:
    contract = load_contract(READY_CONTRACT)
    del contract["claim"]["population"]
    path = tmp_path / "missing-population.yaml"
    path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    code = main(["validate", str(path)])
    captured = capsys.readouterr()

    assert code == 1
    assert captured.err == ""
    assert "Verdict: BLOCK" in captured.out
    assert "CC001 claim.population" in captured.out


def test_schema_does_not_promote_review_only_check_to_structural_failure() -> None:
    contract = load_contract(READY_CONTRACT)
    del contract["evidence"]["checks"]["metric_definition_locked"]

    jsonschema.validate(contract, _schema())
    report = validate_contract(contract)

    assert report.verdict is Verdict.REVIEW
    assert "CC101" in _rule_ids(report)


def test_schema_does_not_encode_conditional_claim_support_rules() -> None:
    contract = load_contract(BLOCK_CONTRACT)

    jsonschema.validate(contract, _schema())
    report = validate_contract(contract)

    assert report.verdict is Verdict.BLOCK
    assert "CC301" in _rule_ids(report)


def test_blank_conditional_comparison_value_remains_rule_engine_concern() -> None:
    contract = load_contract(BLOCK_CONTRACT)
    contract["claim"]["comparison"]["baseline"] = ""

    jsonschema.validate(contract, _schema())
    report = validate_contract(contract)

    assert report.verdict is Verdict.BLOCK
    assert "CC201" in _rule_ids(report)


def test_schema_rejects_wrong_primitive_type() -> None:
    contract = load_contract(READY_CONTRACT)
    contract["evidence"]["sample_size"] = "18420"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(contract, _schema())


def test_schema_allows_additive_metadata() -> None:
    contract = deepcopy(load_contract(READY_CONTRACT))
    contract["workflow_metadata"] = {"run_id": "example-123"}
    contract["evidence"]["provenance"]["query_revision"] = "abc123"

    jsonschema.validate(contract, _schema())
