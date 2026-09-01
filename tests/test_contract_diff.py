from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import yaml

from claim_contract.cli import main
from claim_contract.contract_diff import build_contract_diff
from claim_contract.io import load_contract

ROOT = Path(__file__).parents[1]
READY_CONTRACT = ROOT / "examples/descriptive_summary/contract.yaml"
BLOCK_CONTRACT = ROOT / "examples/onboarding_conversion/contract.yaml"


def test_contract_diff_ignores_mapping_key_order() -> None:
    before = load_contract(READY_CONTRACT)
    after = dict(reversed(list(before.items())))

    diff = build_contract_diff(before, after)

    assert diff.changed is False
    assert diff.changes == ()
    assert diff.before_verdict == "READY"
    assert diff.after_verdict == "READY"


def test_contract_diff_distinguishes_missing_from_null() -> None:
    before = load_contract(READY_CONTRACT)
    after = deepcopy(before)
    after["evidence"]["uncertainty"] = None

    diff = build_contract_diff(before, after)

    uncertainty = next(change for change in diff.changes if change.path == "evidence.uncertainty")
    assert uncertainty.change_type == "changed"
    assert uncertainty.before_present is True
    assert uncertainty.after_present is True
    assert uncertainty.after is None

    missing_after = deepcopy(after)
    del missing_after["evidence"]["uncertainty"]
    missing_diff = build_contract_diff(after, missing_after)
    removed = next(change for change in missing_diff.changes if change.path == "evidence.uncertainty")
    assert removed.change_type == "removed"
    assert removed.before_present is True
    assert removed.after_present is False


def test_contract_diff_reports_verdict_transition() -> None:
    before = load_contract(BLOCK_CONTRACT)
    after = load_contract(READY_CONTRACT)

    diff = build_contract_diff(before, after)
    payload = diff.to_dict()

    assert payload["verdict_transition"] == {
        "before": "BLOCK",
        "after": "READY",
        "changed": True,
    }
    assert payload["scientific_validation"] is False
    assert payload["automatic_interpretation"] is False
    assert payload["change_count"] == len(payload["changes"])
    assert payload["changes"] == sorted(payload["changes"], key=lambda item: item["path"])


def test_cli_contract_diff_json(capsys) -> None:
    code = main(
        [
            "contract",
            "diff",
            str(BLOCK_CONTRACT),
            str(READY_CONTRACT),
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["type"] == "claim_contract.contract_diff"
    assert payload["verdict_transition"]["before"] == "BLOCK"
    assert payload["verdict_transition"]["after"] == "READY"
    assert payload["changes"]


def test_cli_contract_diff_text(capsys) -> None:
    code = main(
        [
            "contract",
            "diff",
            str(BLOCK_CONTRACT),
            str(READY_CONTRACT),
        ]
    )

    assert code == 0
    output = capsys.readouterr().out
    assert "Verdict: BLOCK -> READY" in output
    assert "Changed fields:" in output
    assert "claim.text" in output
    assert "Scientific validation: false" in output


def test_cli_contract_diff_rejects_two_stdin_sources(capsys) -> None:
    code = main(["contract", "diff", "-", "-"])

    assert code == 2
    assert "only one side" in capsys.readouterr().err.lower()


def test_cli_contract_diff_input_error(capsys, tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    code = main(["contract", "diff", str(invalid), str(READY_CONTRACT), "--json"])

    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["type"] == "claim_contract.error"
    assert "root must be an object" in payload["message"].lower()


def test_cli_contract_diff_yaml_formatting_is_not_a_change(capsys, tmp_path: Path) -> None:
    contract = load_contract(READY_CONTRACT)
    reformatted = tmp_path / "reformatted.yaml"
    reformatted.write_text(yaml.safe_dump(contract, sort_keys=True), encoding="utf-8")

    code = main(["contract", "diff", str(READY_CONTRACT), str(reformatted), "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contract_changed"] is False
    assert payload["change_count"] == 0
