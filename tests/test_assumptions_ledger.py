from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from claim_contract import load_contract, validate_contract
from claim_contract.binding import build_contract_binding, build_profile_manifest_binding
from claim_contract.profiles import get_profile_manifest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "assumptions-ledger-v1.schema.json"
EXAMPLE_DIR = ROOT / "examples" / "assumptions_ledger"
LEDGER_PATH = EXAMPLE_DIR / "ledger.yaml"
CONTRACT_PATH = EXAMPLE_DIR / "contract.yaml"


def _load_schema() -> dict[str, object]:
    value = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _load_ledger() -> dict[str, object]:
    value = yaml.safe_load(LEDGER_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_load_schema(), format_checker=FormatChecker())


def test_assumptions_ledger_schema_and_example_are_valid() -> None:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    _validator().validate(_load_ledger())


def test_example_binds_exact_contract_and_profile_semantics() -> None:
    ledger = _load_ledger()
    contract = load_contract(CONTRACT_PATH)

    assert ledger["claim_text"] == contract["claim"]["text"]
    assert ledger["contract"]["version"] == contract["version"]
    assert ledger["contract"]["profile"] == contract["profile"]
    assert ledger["contract"]["input_binding"] == build_contract_binding(contract).to_dict()

    manifest = get_profile_manifest(contract["profile"])
    assert ledger["contract"]["profile_manifest_binding"] == (
        build_profile_manifest_binding(manifest.to_dict()).to_dict()
    )


def test_example_assumption_ids_are_unique() -> None:
    ledger = _load_ledger()
    ids = [assumption["id"] for assumption in ledger["assumptions"]]
    assert len(ids) == len(set(ids))


def test_open_status_rejects_lifecycle_history() -> None:
    ledger = deepcopy(_load_ledger())
    assumption = ledger["assumptions"][0]
    assumption["status"] = "OPEN"

    with pytest.raises(ValidationError):
        _validator().validate(ledger)


def test_reviewed_status_requires_review_record() -> None:
    ledger = deepcopy(_load_ledger())
    assumption = ledger["assumptions"][0]
    assumption["review"] = None

    with pytest.raises(ValidationError):
        _validator().validate(ledger)


def test_challenged_status_requires_review_and_challenge_records() -> None:
    ledger = deepcopy(_load_ledger())
    assumption = ledger["assumptions"][1]
    assumption["challenge"] = None

    with pytest.raises(ValidationError):
        _validator().validate(ledger)


def test_retired_status_requires_retirement_record() -> None:
    ledger = deepcopy(_load_ledger())
    assumption = ledger["assumptions"][0]
    assumption["status"] = "RETIRED"

    with pytest.raises(ValidationError):
        _validator().validate(ledger)


def test_assumptions_ledger_does_not_change_minimum_v0_1_verdict_semantics() -> None:
    contract = load_contract(CONTRACT_PATH)
    report = validate_contract(contract)

    assert report.verdict.value == "REVIEW"
    assert {finding.rule_id for finding in report.findings} == {"CC305"}
