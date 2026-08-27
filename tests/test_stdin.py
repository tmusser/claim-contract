from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from claim_contract.cli import main
from claim_contract.io import load_contract

ROOT = Path(__file__).parents[1]
READY_CONTRACT = ROOT / "examples/descriptive_summary/contract.yaml"
REVIEW_CONTRACT = ROOT / "examples/missing_uncertainty/contract.yaml"
BLOCK_CONTRACT = ROOT / "examples/onboarding_conversion/contract.yaml"


def _pipe(monkeypatch, text: str) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))


def test_validate_stdin_yaml_matches_file_json(monkeypatch, capsys) -> None:
    file_code = main(["validate", str(READY_CONTRACT), "--json"])
    file_payload = json.loads(capsys.readouterr().out)

    _pipe(monkeypatch, READY_CONTRACT.read_text(encoding="utf-8"))
    stdin_code = main(["validate", "-", "--json"])
    stdin_payload = json.loads(capsys.readouterr().out)

    assert stdin_code == file_code == 0
    assert stdin_payload == file_payload


def test_validate_stdin_accepts_json_without_filename_extension(monkeypatch, capsys) -> None:
    contract = load_contract(READY_CONTRACT)
    _pipe(monkeypatch, json.dumps(contract))

    code = main(["validate", "-", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["verdict"] == "READY"
    assert payload["contract"]["input_binding"]["contract_sha256"]


def test_validate_stdin_preserves_block_exit_and_text_output(monkeypatch, capsys) -> None:
    _pipe(monkeypatch, BLOCK_CONTRACT.read_text(encoding="utf-8"))

    code = main(["validate", "-"])
    output = capsys.readouterr().out

    assert code == 1
    assert "Verdict: BLOCK" in output
    assert "CC301" in output


def test_validate_stdin_preserves_review_warnings_as_errors(monkeypatch, capsys) -> None:
    text = REVIEW_CONTRACT.read_text(encoding="utf-8")

    _pipe(monkeypatch, text)
    default_code = main(["validate", "-", "--json"])
    default_payload = json.loads(capsys.readouterr().out)

    _pipe(monkeypatch, text)
    strict_code = main(["validate", "-", "--json", "--warnings-as-errors"])
    strict_payload = json.loads(capsys.readouterr().out)

    assert default_code == 0
    assert strict_code == 1
    assert default_payload == strict_payload
    assert default_payload["verdict"] == "REVIEW"


def test_validate_malformed_stdin_keeps_json_error_envelope(monkeypatch, capsys) -> None:
    _pipe(monkeypatch, "claim: [unterminated")

    code = main(["validate", "-", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["type"] == "claim_contract.error"
    assert payload["error"]["code"] == "INPUT_ERROR"
    assert payload["scientific_validation"] is False


def test_chart_handoff_can_reuse_stdin_contract_input(monkeypatch, capsys) -> None:
    _pipe(monkeypatch, READY_CONTRACT.read_text(encoding="utf-8"))

    code = main(["handoff", "chart", "-"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["type"] == "claim_contract.chart_handoff"
    assert payload["validation"]["verdict"] == "READY"
