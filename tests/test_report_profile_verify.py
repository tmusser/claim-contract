from __future__ import annotations

import json
from pathlib import Path

from claim_contract import load_contract, validate_contract
from claim_contract.cli import main

ROOT = Path(__file__).parents[1]
CONTRACT_PATH = ROOT / "examples/descriptive_summary/contract.yaml"


def _write_report(path: Path) -> dict:
    payload = validate_contract(load_contract(CONTRACT_PATH)).to_dict()
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_report_verify_checks_profile_manifest_binding(tmp_path: Path, capsys) -> None:
    report_path = tmp_path / "report.json"
    _write_report(report_path)

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
    assert "Profile manifest SHA-256: MATCH" in captured.out
    assert "Saved profile manifest SHA-256:" in captured.out
    assert "Current profile manifest SHA-256:" in captured.out


def test_report_verify_returns_one_for_profile_manifest_drift(
    tmp_path: Path, capsys
) -> None:
    report_path = tmp_path / "report.json"
    payload = _write_report(report_path)
    payload["contract"]["profile_manifest_binding"][
        "profile_manifest_sha256"
    ] = "0" * 64
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

    assert code == 1
    assert captured.err == ""
    assert "Binding: MISMATCH" in captured.out
    assert "Contract SHA-256: MATCH" in captured.out
    assert "Profile manifest SHA-256: MISMATCH" in captured.out


def test_report_verify_legacy_profile_unbound_keeps_contract_semantics(
    tmp_path: Path, capsys
) -> None:
    report_path = tmp_path / "report.json"
    payload = _write_report(report_path)
    del payload["contract"]["profile_manifest_binding"]
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

    assert code == 0
    assert captured.err == ""
    assert "Binding: MATCH" in captured.out
    assert "Contract SHA-256: MATCH" in captured.out
    assert "Profile manifest SHA-256: UNBOUND" in captured.out


def test_report_verify_rejects_malformed_profile_binding(
    tmp_path: Path, capsys
) -> None:
    report_path = tmp_path / "report.json"
    payload = _write_report(report_path)
    payload["contract"]["profile_manifest_binding"][
        "profile_manifest_sha256"
    ] = "not-a-sha"
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
    assert "profile_manifest_sha256" in captured.err
