from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from claim_contract import (
    build_profile_manifest_binding,
    get_profile_manifest,
    load_contract,
    validate_contract,
)
from claim_contract.cli import main


ROOT = Path(__file__).parents[1]
CONTRACT_PATH = ROOT / "examples/descriptive_summary/contract.yaml"


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _current_report_payload() -> dict:
    contract = load_contract(CONTRACT_PATH)
    return validate_contract(contract).to_dict()


def _current_manifest() -> dict:
    return get_profile_manifest("minimum-v0.1").to_dict()


def test_supplied_frozen_manifest_can_match_historical_report_after_installed_drift(
    tmp_path: Path, capsys
) -> None:
    payload = _current_report_payload()
    historical_manifest = deepcopy(_current_manifest())
    historical_manifest["rules"][0]["trigger"] += " Historical wording."
    payload["contract"]["profile_manifest_binding"] = (
        build_profile_manifest_binding(historical_manifest).to_dict()
    )

    report_path = _write_json(tmp_path / "report.json", payload)
    manifest_path = _write_json(tmp_path / "historical-profile.json", historical_manifest)

    current_code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
        ]
    )
    current_output = capsys.readouterr()

    assert current_code == 1
    assert current_output.err == ""
    assert "Binding: MISMATCH" in current_output.out
    assert "Profile manifest SHA-256: MISMATCH" in current_output.out
    assert "Current profile manifest SHA-256:" in current_output.out

    historical_code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
            "--profile-manifest",
            str(manifest_path),
        ]
    )
    historical_output = capsys.readouterr()

    assert historical_code == 0
    assert historical_output.err == ""
    assert "Binding: MATCH" in historical_output.out
    assert "Contract SHA-256: MATCH" in historical_output.out
    assert "Profile manifest SHA-256: MATCH" in historical_output.out
    assert "Supplied profile manifest SHA-256:" in historical_output.out
    assert "Supplied profile: minimum-v0.1" in historical_output.out
    assert "Bound profile: minimum-v0.1" in historical_output.out


def test_valid_but_different_supplied_manifest_is_identity_mismatch(
    tmp_path: Path, capsys
) -> None:
    payload = _current_report_payload()
    changed_manifest = deepcopy(_current_manifest())
    changed_manifest["rules"][0]["known_boundary"] += " Changed boundary."

    report_path = _write_json(tmp_path / "report.json", payload)
    manifest_path = _write_json(tmp_path / "changed-profile.json", changed_manifest)

    code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
            "--profile-manifest",
            str(manifest_path),
        ]
    )
    captured = capsys.readouterr()

    assert code == 1
    assert captured.err == ""
    assert "Binding: MISMATCH" in captured.out
    assert "Profile manifest SHA-256: MISMATCH" in captured.out
    assert "Supplied profile manifest SHA-256:" in captured.out


def test_supplied_manifest_for_different_profile_is_mismatch_not_parser_error(
    tmp_path: Path, capsys
) -> None:
    payload = _current_report_payload()
    other_manifest = deepcopy(_current_manifest())
    other_manifest["profile"]["name"] = "minimum-v0.1-archive"

    report_path = _write_json(tmp_path / "report.json", payload)
    manifest_path = _write_json(tmp_path / "other-profile.json", other_manifest)

    code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
            "--profile-manifest",
            str(manifest_path),
        ]
    )
    captured = capsys.readouterr()

    assert code == 1
    assert captured.err == ""
    assert "Profile manifest SHA-256: MISMATCH" in captured.out
    assert "Supplied profile: minimum-v0.1-archive" in captured.out
    assert "Bound profile: minimum-v0.1" in captured.out


def test_supplied_manifest_tool_version_only_drift_still_matches(
    tmp_path: Path, capsys
) -> None:
    payload = _current_report_payload()
    release_only_manifest = deepcopy(_current_manifest())
    release_only_manifest["tool"]["version"] = "0.0.1-historical"

    report_path = _write_json(tmp_path / "report.json", payload)
    manifest_path = _write_json(tmp_path / "release-only.json", release_only_manifest)

    code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
            "--profile-manifest",
            str(manifest_path),
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    assert "Binding: MATCH" in captured.out
    assert "Profile manifest SHA-256: MATCH" in captured.out


def test_malformed_supplied_manifest_is_input_error(tmp_path: Path, capsys) -> None:
    payload = _current_report_payload()
    report_path = _write_json(tmp_path / "report.json", payload)
    manifest_path = _write_json(tmp_path / "bad-profile.json", {"type": "wrong"})

    code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
            "--profile-manifest",
            str(manifest_path),
        ]
    )
    captured = capsys.readouterr()

    assert code == 2
    assert captured.out == ""
    assert "Input error:" in captured.err
    assert "Invalid profile manifest shape" in captured.err


def test_supplied_manifest_cannot_retroactively_bind_profile_unbound_report(
    tmp_path: Path, capsys
) -> None:
    payload = _current_report_payload()
    del payload["contract"]["profile_manifest_binding"]

    report_path = _write_json(tmp_path / "legacy.json", payload)
    manifest_path = _write_json(tmp_path / "profile.json", _current_manifest())

    legacy_code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
        ]
    )
    legacy_output = capsys.readouterr()

    assert legacy_code == 0
    assert legacy_output.err == ""
    assert "Binding: MATCH" in legacy_output.out
    assert "Profile manifest SHA-256: UNBOUND" in legacy_output.out

    supplied_code = main(
        [
            "report",
            "verify",
            str(report_path),
            "--contract",
            str(CONTRACT_PATH),
            "--profile-manifest",
            str(manifest_path),
        ]
    )
    supplied_output = capsys.readouterr()

    assert supplied_code == 2
    assert supplied_output.out == ""
    assert "cannot retroactively bind an unbound report" in supplied_output.err
