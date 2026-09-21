from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import jsonschema
import yaml

from claim_contract import build_contract_binding, load_contract
from claim_contract.cli import main
from claim_contract.receipts import (
    RECEIPTED,
    UNRECEIPTED,
    inspect_evidence_receipts,
)


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "examples" / "descriptive_summary" / "contract.yaml"
INPUT_SCHEMA = ROOT / "schemas" / "evidence-receipts-v1.schema.json"
OUTPUT_SCHEMA = ROOT / "schemas" / "evidence-receipt-inspection-v1.schema.json"
GOOD_REF = "docs/RULE_TRACE.md"
SCOPE_NOTICE = (
    "These receipts record retained repository references only and do not verify "
    "that the referenced material proves or adequately supports a declaration."
)


def _schema(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _head_revision() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _payload(
    contract: dict,
    receipts: list[dict],
    *,
    revision: str | None = None,
) -> dict:
    return {
        "schema_version": "1.0",
        "type": "claim_contract.evidence_receipts",
        "scientific_validation": False,
        "automatic_verification": False,
        "scope_notice": SCOPE_NOTICE,
        "contract": {
            "input_binding": build_contract_binding(contract).to_dict(),
        },
        "snapshot": {
            "repository_revision": revision or _head_revision(),
        },
        "receipts": receipts,
    }


def _write_payload(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "receipts.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_receipt_schemas_are_valid_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema(INPUT_SCHEMA))
    jsonschema.Draft202012Validator.check_schema(_schema(OUTPUT_SCHEMA))


def test_receipt_input_fixture_matches_published_schema() -> None:
    contract = load_contract(CONTRACT)
    payload = _payload(
        contract,
        [
            {
                "field": "evidence.design",
                "refs": [GOOD_REF],
                "note": "Retained design note.",
            }
        ],
    )

    jsonschema.validate(payload, _schema(INPUT_SCHEMA))


def test_inspection_derives_applicable_evidence_fields_from_rule_trace() -> None:
    contract = load_contract(CONTRACT)
    payload = _payload(
        contract,
        [
            {"field": "evidence.design", "refs": [GOOD_REF]},
            {
                "field": "evidence.checks.missingness_assessed",
                "refs": [GOOD_REF],
            },
            {
                "field": "evidence.checks.treatment_assignment_validated",
                "refs": [GOOD_REF],
            },
        ],
    )

    inspection = inspect_evidence_receipts(
        contract,
        payload,
        contract_path=CONTRACT,
    )
    result = inspection.to_dict()
    jsonschema.validate(result, _schema(OUTPUT_SCHEMA))

    by_field = {item.field: item for item in inspection.coverage}
    assert set(by_field) == {
        "evidence.design",
        "evidence.sample_size",
        "evidence.provenance.source",
        "evidence.checks.metric_definition_locked",
        "evidence.checks.missingness_assessed",
    }
    assert by_field["evidence.design"].status == RECEIPTED
    assert by_field["evidence.design"].applicable_rule_ids == ("CC001",)
    assert by_field["evidence.checks.missingness_assessed"].status == RECEIPTED
    assert by_field["evidence.sample_size"].status == UNRECEIPTED
    assert by_field["evidence.sample_size"].refs_resolve is None

    assert [receipt.field for receipt in inspection.unused_receipts] == [
        "evidence.checks.treatment_assignment_validated"
    ]
    assert inspection.integrity_ok is True
    assert inspection.profile == "minimum-v0.1"
    assert len(inspection.profile_manifest_binding.profile_manifest_sha256) == 64
    assert result["contract"]["profile_manifest_binding"]["canonicalization"] == (
        "profile-manifest-semantics-v1"
    )
    assert inspection.receipted_count == 2
    assert inspection.unreceipted_count == 3


def test_missing_receipts_are_informational_and_do_not_fail_cli(
    capsys, tmp_path: Path
) -> None:
    contract = load_contract(CONTRACT)
    payload = _payload(contract, [])
    receipts_path = _write_payload(tmp_path, payload)

    code = main(
        [
            "receipts",
            "inspect",
            str(CONTRACT),
            str(receipts_path),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert code == 0
    assert captured.err == ""
    assert result["summary"]["integrity_ok"] is True
    assert result["summary"]["receipted_count"] == 0
    assert result["summary"]["unreceipted_count"] > 0
    assert result["changes_validation_verdict"] is False


def test_missing_pinned_ref_is_integrity_failure_not_scientific_failure(
    capsys, tmp_path: Path
) -> None:
    contract = load_contract(CONTRACT)
    payload = _payload(
        contract,
        [
            {
                "field": "evidence.design",
                "refs": ["artifacts/does-not-exist.json"],
            }
        ],
    )
    receipts_path = _write_payload(tmp_path, payload)

    code = main(
        [
            "receipts",
            "inspect",
            str(CONTRACT),
            str(receipts_path),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    jsonschema.validate(result, _schema(OUTPUT_SCHEMA))

    assert code == 1
    assert result["summary"]["integrity_ok"] is False
    assert result["scientific_validation"] is False
    assert result["automatic_verification"] is False
    assert result["snapshot"]["missing_refs"] == [
        "artifacts/does-not-exist.json"
    ]
    coverage = {item["field"]: item for item in result["coverage"]}
    assert coverage["evidence.design"]["status"] == "RECEIPTED"
    assert coverage["evidence.design"]["refs_resolve"] is False


def test_stale_contract_binding_refuses_to_attribute_coverage(
    capsys, tmp_path: Path
) -> None:
    contract = load_contract(CONTRACT)
    stale_contract = deepcopy(contract)
    stale_contract["evidence"]["sample_size"] += 1
    payload = _payload(
        stale_contract,
        [{"field": "evidence.design", "refs": [GOOD_REF]}],
    )
    receipts_path = _write_payload(tmp_path, payload)

    code = main(
        [
            "receipts",
            "inspect",
            str(CONTRACT),
            str(receipts_path),
            "--json",
        ]
    )
    result = json.loads(capsys.readouterr().out)

    assert code == 1
    assert result["contract"]["binding_match"] is False
    assert result["summary"]["integrity_ok"] is False
    assert result["coverage"] == []
    assert result["summary"]["applicable_evidence_field_count"] == 0
    assert [item["field"] for item in result["unused_receipts"]] == [
        "evidence.design"
    ]


def test_stale_binding_with_removed_field_remains_binding_mismatch(
    capsys, tmp_path: Path
) -> None:
    current = load_contract(CONTRACT)
    older = deepcopy(current)
    older["evidence"]["legacy_support"] = "retained"
    payload = _payload(
        older,
        [{"field": "evidence.legacy_support", "refs": [GOOD_REF]}],
    )
    receipts_path = _write_payload(tmp_path, payload)

    code = main(
        [
            "receipts",
            "inspect",
            str(CONTRACT),
            str(receipts_path),
            "--json",
        ]
    )
    result = json.loads(capsys.readouterr().out)

    assert code == 1
    assert result["contract"]["binding_match"] is False
    assert result["coverage"] == []
    assert result["unused_receipts"][0]["field"] == "evidence.legacy_support"


def test_unsafe_repository_ref_is_reported_without_dereferencing(
    capsys, tmp_path: Path
) -> None:
    contract = load_contract(CONTRACT)
    payload = _payload(
        contract,
        [{"field": "evidence.design", "refs": ["../secret.txt"]}],
    )
    receipts_path = _write_payload(tmp_path, payload)

    code = main(
        [
            "receipts",
            "inspect",
            str(CONTRACT),
            str(receipts_path),
            "--json",
        ]
    )
    result = json.loads(capsys.readouterr().out)

    assert code == 1
    assert result["snapshot"]["invalid_refs"] == ["../secret.txt"]
    assert result["summary"]["integrity_ok"] is False


def test_receipt_field_must_exist_in_current_contract(capsys, tmp_path: Path) -> None:
    contract = load_contract(CONTRACT)
    payload = _payload(
        contract,
        [{"field": "evidence.checks.imaginary_check", "refs": [GOOD_REF]}],
    )
    receipts_path = _write_payload(tmp_path, payload)

    code = main(
        [
            "receipts",
            "inspect",
            str(CONTRACT),
            str(receipts_path),
        ]
    )
    captured = capsys.readouterr()

    assert code == 2
    assert "does not exist in the supplied contract" in captured.err


def test_receipts_cannot_claim_automatic_or_scientific_verification(
    capsys, tmp_path: Path
) -> None:
    contract = load_contract(CONTRACT)
    payload = _payload(contract, [])
    payload["automatic_verification"] = True
    receipts_path = _write_payload(tmp_path, payload)

    code = main(
        [
            "receipts",
            "inspect",
            str(CONTRACT),
            str(receipts_path),
            "--json",
        ]
    )
    captured = capsys.readouterr()

    assert code == 2
    error = json.loads(captured.out)
    assert error["type"] == "claim_contract.error"
    assert "automatic_verification: false" in error["error"]["message"]


def test_inspection_does_not_mutate_contract() -> None:
    contract = load_contract(CONTRACT)
    before = deepcopy(contract)
    payload = _payload(contract, [])

    inspect_evidence_receipts(contract, payload, contract_path=CONTRACT)

    assert contract == before
