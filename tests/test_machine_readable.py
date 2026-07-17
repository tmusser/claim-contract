from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest

from claim_contract import load_contract, validate_contract
from claim_contract.cli import main
from claim_contract.formatters import error_payload

ROOT = Path(__file__).parents[1]
SCHEMAS = ROOT / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_published_schemas_are_valid_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(load_schema("report-v1.schema.json"))
    jsonschema.Draft202012Validator.check_schema(load_schema("error-v1.schema.json"))


@pytest.mark.parametrize(
    "contract_path",
    sorted((ROOT / "examples").rglob("contract.yaml")),
    ids=lambda path: str(path.relative_to(ROOT / "examples")),
)
def test_every_example_report_matches_report_v1_schema(contract_path: Path) -> None:
    report = validate_contract(load_contract(contract_path)).to_dict()

    jsonschema.validate(report, load_schema("report-v1.schema.json"))
    assert report["schema_version"] == "1.0"
    assert report["type"] == "claim_contract.report"
    assert report["tool"]["name"] == "claim-contract"
    assert report["contract"]["profile"] == report["profile"]
    assert report["summary"]["finding_count"] == len(report["findings"])
    assert report["summary"]["review_count"] == sum(
        finding["severity"] == "REVIEW" for finding in report["findings"]
    )
    assert report["summary"]["block_count"] == sum(
        finding["severity"] == "BLOCK" for finding in report["findings"]
    )


def test_report_schema_rejects_removed_scope_notice() -> None:
    report = validate_contract(
        load_contract(ROOT / "examples/descriptive_summary/contract.yaml")
    ).to_dict()
    stripped = deepcopy(report)
    del stripped["scope_notice"]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(stripped, load_schema("report-v1.schema.json"))


def test_report_schema_rejects_scientific_validation_true() -> None:
    report = validate_contract(
        load_contract(ROOT / "examples/descriptive_summary/contract.yaml")
    ).to_dict()
    overstated = deepcopy(report)
    overstated["scientific_validation"] = True

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(overstated, load_schema("report-v1.schema.json"))


def test_error_payload_matches_error_v1_schema() -> None:
    payload = error_payload("Input error: malformed contract")

    jsonschema.validate(payload, load_schema("error-v1.schema.json"))
    assert payload["schema_version"] == "1.0"
    assert payload["type"] == "claim_contract.error"
    assert payload["scientific_validation"] is False
    assert payload["not_evaluated"]


def test_cli_json_input_error_is_one_structured_document(capsys, tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"

    code = main(["validate", str(missing), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 2
    assert captured.err == ""
    assert payload["error"]["code"] == "INPUT_ERROR"
    jsonschema.validate(payload, load_schema("error-v1.schema.json"))
