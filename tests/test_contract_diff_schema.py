from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from claim_contract.contract_diff import build_contract_diff
from claim_contract.io import load_contract

ROOT = Path(__file__).parents[1]


def test_contract_diff_schema_is_valid_and_accepts_generated_output() -> None:
    schema = json.loads((ROOT / "schemas/contract-diff-v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    before = load_contract(ROOT / "examples/onboarding_conversion/contract.yaml")
    after = load_contract(ROOT / "examples/descriptive_summary/contract.yaml")
    payload = build_contract_diff(before, after).to_dict()

    Draft202012Validator(schema).validate(payload)
