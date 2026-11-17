"""Regression coverage for deterministic packet/contract/report handoff consistency."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from claim_contract.cli import main
from claim_contract.io import load_contract
from claim_contract.packet_consistency import PACKET_VERIFY_SCOPE_NOTICE
from claim_contract.validator import validate_contract


def _fixture(tmp_path: Path, *, two: bool = False) -> tuple[Path, dict]:
    root = tmp_path / "packet"
    (root / "contracts").mkdir(parents=True)
    (root / "validate").mkdir()
    contract = load_contract("examples/onboarding_conversion/contract.yaml")
    (root / "contracts/C01.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=False), encoding="utf-8",
    )
    report = validate_contract(contract).to_dict()
    (root / "validate/C01.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8",
    )

    findings = "; ".join(
        f"{x['rule_id']}/{x['severity']}/{x['path']}"
        for x in report["findings"]
    ) or "-"
    table = [
        "# Review packet",
        "Operator notes go here.",
        "",
        "## Validation summary",
        "",
        "| Contract | Claim text | Verdict | Findings | Report |",
        "| --- | --- | --- | --- | --- |",
        (
            "| [C01](contracts/C01.yaml) | "
            f"{report['claim_text']} | {report['verdict']} | {findings} | "
            "[JSON](validate/C01.json) |"
        ),
    ]
    if two:
        second = load_contract("examples/descriptive_summary/contract.yaml")
        (root / "contracts/C02.yaml").write_text(
            yaml.safe_dump(second, sort_keys=False), encoding="utf-8",
        )
        second_report = validate_contract(second).to_dict()
        (root / "validate/C02.json").write_text(
            json.dumps(second_report), encoding="utf-8",
        )
        assert second_report["verdict"] == "READY"
        table.append(
            f"| [C02](contracts/C02.yaml) | {second_report['claim_text']} "
            "| READY | - | [JSON](validate/C02.json) |"
        )
    table += ["", "Other narrative sections remain unrestricted.", ""]
    packet = root / "packet.md"
    packet.write_text("\n".join(table), encoding="utf-8")
    return packet, report


def _rewrite(packet: Path, before: str, after: str) -> None:
    text = packet.read_text(encoding="utf-8")
    assert before in text
    packet.write_text(text.replace(before, after), encoding="utf-8")


def _codes(capsys) -> set[str]:
    payload = json.loads(capsys.readouterr().out)
    return {finding["code"] for finding in payload["failures"]}


def test_valid_report_and_contract_summary_passes(tmp_path, capsys):
    packet, _ = _fixture(tmp_path, two=True)
    before = [(p, p.read_bytes()) for p in packet.parent.rglob("*") if p.is_file()]
    assert main(["packet", "verify", str(packet), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["rows_checked"] == 2
    assert payload["failures"] == []
    assert payload["scope_notice"] == PACKET_VERIFY_SCOPE_NOTICE
    assert payload["scientific_validation"] is False
    assert payload["automatic_adjudication"] is False
    assert payload["type"] == "claim_contract.packet_consistency_check"
    assert before == [(p, p.read_bytes()) for p in packet.parent.rglob("*") if p.is_file()]


def test_packet_verdict_mismatch_is_detected(tmp_path, capsys):
    packet, _ = _fixture(tmp_path)
    _rewrite(packet, " | BLOCK | ", " | READY | ")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert "VERDICT_MISMATCH" in _codes(capsys)


def test_changed_claim_text_is_detected_even_if_verdict_is_same(tmp_path, capsys):
    packet, report = _fixture(tmp_path)
    _rewrite(packet, report["claim_text"], "The redesign improved activation.")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert {"CLAIM_TEXT", "REPORT_CLAIM_TEXT"} <= _codes(capsys)


def test_missing_and_extra_findings_are_detected(tmp_path, capsys):
    packet, report = _fixture(tmp_path)
    finding = report["findings"][0]
    token = f"{finding['rule_id']}/{finding['severity']}/{finding['path']}"
    _rewrite(packet, token + "; ", "")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert "FINDINGS_MISMATCH" in _codes(capsys)


def test_malformed_findings_fail_instead_of_being_ignored(tmp_path, capsys):
    packet, report = _fixture(tmp_path)
    finding = report["findings"][0]
    token = f"{finding['rule_id']}/{finding['severity']}/{finding['path']}"
    _rewrite(packet, token, "some concern")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert "FINDINGS_FORMAT" in _codes(capsys)


def test_tampered_validator_json_is_detected_even_when_table_agrees(tmp_path, capsys):
    packet, report = _fixture(tmp_path)
    path = packet.parent / "validate/C01.json"
    report["findings"][0]["path"] = "claim.population"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    codes = _codes(capsys)
    assert "SAVED_REPORT_DRIFT" in codes
    assert "FINDINGS_MISMATCH" in codes


def test_contract_binding_drift_is_detected(tmp_path, capsys):
    packet, _ = _fixture(tmp_path)
    path = packet.parent / "contracts/C01.yaml"
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    contract["claim"]["population"] = "some other users"
    path.write_text(yaml.safe_dump(contract), encoding="utf-8")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert "SAVED_REPORT_DRIFT" in _codes(capsys)


def test_boolean_number_report_tampering_does_not_compare_equal(tmp_path, capsys):
    packet, report = _fixture(tmp_path)
    path = packet.parent / "validate/C01.json"
    report["scientific_validation"] = 0
    path.write_text(json.dumps(report), encoding="utf-8")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert "SAVED_REPORT_DRIFT" in _codes(capsys)


def test_missing_report_is_finding_not_crash(tmp_path, capsys):
    packet, _ = _fixture(tmp_path)
    (packet.parent / "validate/C01.json").unlink()
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert "MISSING_REPORT" in _codes(capsys)


def test_missing_row_is_detected_from_directory_inventory(tmp_path, capsys):
    packet, _ = _fixture(tmp_path, two=True)
    lines = packet.read_text(encoding="utf-8").splitlines()
    packet.write_text(
        "\n".join(line for line in lines if "[C02]" not in line), encoding="utf-8",
    )
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    codes = _codes(capsys)
    assert {"UNLISTED_CONTRACT", "UNLISTED_REPORT"} <= codes


def test_duplicate_row_is_rejected(tmp_path, capsys):
    packet, _ = _fixture(tmp_path)
    lines = packet.read_text(encoding="utf-8").splitlines()
    lines.insert(8, lines[7])
    packet.write_text("\n".join(lines), encoding="utf-8")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert {"DUPLICATE_CONTRACT", "DUPLICATE_REPORT"} <= _codes(capsys)


def test_mismapped_report_is_rejected(tmp_path, capsys):
    packet, _ = _fixture(tmp_path, two=True)
    _rewrite(packet, "[C01](contracts/C01.yaml)", "[C01](contracts/C02.yaml)")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert "REPORT_MAPPING" in _codes(capsys)


@pytest.mark.parametrize("bad_path", [
    "../outside.yaml",
    "contracts/../../outside.yaml",
    "https://example.test/report.yaml",
    "/absolute/contract.yaml",
    "C:/file.yaml",
])
def test_untrusted_target_rejected(tmp_path, capsys, bad_path):
    packet, _ = _fixture(tmp_path)
    _rewrite(packet, "contracts/C01.yaml", bad_path)
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert "INVALID_TARGET" in _codes(capsys)


def test_invalid_json_is_caught(tmp_path, capsys):
    packet, _ = _fixture(tmp_path)
    (packet.parent / "validate/C01.json").write_text("{", encoding="utf-8")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert "ARTIFACT_INPUT" in _codes(capsys)


def test_table_missing_fails_closed(tmp_path, capsys):
    packet, _ = _fixture(tmp_path)
    _rewrite(packet, "## Validation summary", "## Validation details")
    assert main(["packet", "verify", str(packet), "--json"]) == 1
    assert {"SUMMARY_SECTION", "UNLISTED_CONTRACT", "UNLISTED_REPORT"} <= _codes(capsys)


def test_missing_packet_is_input_error_with_structured_envelope(tmp_path, capsys):
    assert main(["packet", "verify", str(tmp_path / "absent.md"), "--json"]) == 2
    data = json.loads(capsys.readouterr().out)
    assert data["type"] == "claim_contract.packet_consistency_check"
    assert data["scope_notice"] == PACKET_VERIFY_SCOPE_NOTICE
    assert "error" in data
