from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from claim_contract import (
    Report,
    Verdict,
    build_contract_binding,
    load_contract,
    validate_contract,
)
from claim_contract.cli import main

ROOT = Path(__file__).parents[1]
CONTRACT_PATH = ROOT / "examples/descriptive_summary/contract.yaml"


def test_binding_ignores_mapping_key_order() -> None:
    first = {
        "version": "0.1",
        "profile": "minimum-v0.1",
        "claim": {"text": "Observed result.", "type": "descriptive"},
    }
    second = {
        "claim": {"type": "descriptive", "text": "Observed result."},
        "profile": "minimum-v0.1",
        "version": "0.1",
    }

    assert build_contract_binding(first) == build_contract_binding(second)


def test_binding_changes_when_contract_value_changes() -> None:
    contract = load_contract(CONTRACT_PATH)
    changed = deepcopy(contract)
    changed["evidence"]["sample_size"] += 1

    assert build_contract_binding(contract) != build_contract_binding(changed)


def test_report_preserves_original_positional_constructor_order() -> None:
    report = Report(
        Verdict.READY,
        "minimum-v0.1",
        "Observed result.",
        False,
        "legacy scope text",
        ["legacy limitation"],
        [],
    )

    assert report.scientific_validation is False
    assert report.scope_notice == "legacy scope text"
    assert report.not_evaluated == ["legacy limitation"]
    assert report.contract_version is None
    assert report.input_binding is None


def test_report_preserves_contract_version_and_binding() -> None:
    contract = load_contract(CONTRACT_PATH)
    report = validate_contract(contract)
    payload = report.to_dict()

    assert report.matches_contract(contract)
    assert payload["contract"]["version"] == "0.1"
    binding = payload["contract"]["input_binding"]
    assert binding["algorithm"] == "sha256"
    assert binding["canonicalization"] == "parsed-contract-v1"
    assert len(binding["contract_sha256"]) == 64


def test_report_no_longer_matches_after_contract_mutation() -> None:
    contract = load_contract(CONTRACT_PATH)
    report = validate_contract(contract)
    changed = deepcopy(contract)
    changed["claim"]["population"] = "a different population"

    assert report.matches_contract(changed) is False


def test_cli_report_verify_matches_saved_report(tmp_path: Path, capsys) -> None:
    contract = load_contract(CONTRACT_PATH)
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(validate_contract(contract).to_dict()),
        encoding="utf-8",
    )

    code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    assert "Binding: MATCH" in captured.out
    assert "Contract SHA-256: MATCH" in captured.out
    assert "Bound contract version: 0.1" in captured.out
    assert "Bound profile: minimum-v0.1" in captured.out


def test_cli_report_verify_returns_one_for_contract_drift(
    tmp_path: Path, capsys
) -> None:
    contract = load_contract(CONTRACT_PATH)
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(validate_contract(contract).to_dict()),
        encoding="utf-8",
    )

    changed = deepcopy(contract)
    changed["evidence"]["sample_size"] += 1
    changed_path = tmp_path / "changed.json"
    changed_path.write_text(json.dumps(changed), encoding="utf-8")

    code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(changed_path),
        ]
    )
    captured = capsys.readouterr()

    assert code == 1
    assert captured.err == ""
    assert "Binding: MISMATCH" in captured.out
    assert "Contract SHA-256: MISMATCH" in captured.out


def test_cli_report_verify_rejects_unbound_legacy_report(
    tmp_path: Path, capsys
) -> None:
    contract = load_contract(CONTRACT_PATH)
    payload = validate_contract(contract).to_dict()
    del payload["contract"]["input_binding"]
    report_path = tmp_path / "legacy.json"
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
        ]
    )
    captured = capsys.readouterr()

    assert code == 2
    assert captured.out == ""
    assert "contract.input_binding" in captured.err
