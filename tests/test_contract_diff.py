from __future__ import annotations

import json
from copy import deepcopy
from io import StringIO
from pathlib import Path

import pytest
import yaml

from claim_contract.cli import main
from claim_contract.contract_diff import build_contract_diff
from claim_contract.io import load_contract
from claim_contract.validator import validate_contract

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
    assert "root must be an object" in payload["error"]["message"].lower()


def test_cli_contract_diff_yaml_formatting_is_not_a_change(capsys, tmp_path: Path) -> None:
    contract = load_contract(READY_CONTRACT)
    reformatted = tmp_path / "reformatted.yaml"
    reformatted.write_text(yaml.safe_dump(contract, sort_keys=True), encoding="utf-8")

    code = main(["contract", "diff", str(READY_CONTRACT), str(reformatted), "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contract_changed"] is False
    assert payload["change_count"] == 0


@pytest.fixture
def review_baseline() -> dict:
    # Deliberately incomplete synthetic declarations keep both verdicts BLOCK.
    return {
        "version": "0.1",
        "profile": "minimum-v0.1",
        "claim": {"text": "The rate is still higher in group B.", "type": "comparison"},
        "evidence": {"checks": {"missingness_assessed": False}},
    }


@pytest.mark.parametrize(
    ("path", "proposed_value"),
    [
        ("claim.text", "The rate is higher in group B."),
        ("claim.type", "descriptive"),
        ("claim.population", "Synthetic population inferred by a reviewer"),
        ("claim.population", None),
        ("evidence.checks.missingness_assessed", True),
        ("evidence.checks.missingness_assessed", 0),
    ],
)
@pytest.mark.parametrize("output_format", ["text", "json"])
def test_cli_contract_diff_gates_review_edits(
    review_baseline, tmp_path, capsys, path, proposed_value, output_format
) -> None:
    proposed = deepcopy(review_baseline)
    parent, field = path.rsplit(".", 1)
    target = proposed
    for part in parent.split("."):
        target = target[part]
    target[field] = proposed_value
    before = tmp_path / "baseline.json"
    after = tmp_path / "returned.json"
    before.write_text(json.dumps(review_baseline), encoding="utf-8")
    after.write_text(json.dumps(proposed), encoding="utf-8")

    code = main([
        "contract", "diff", str(before), str(after),
        "--fail-on-change", "--format", output_format,
    ])

    assert code == 1
    output = capsys.readouterr().out
    if output_format == "json":
        payload = json.loads(output)
        assert payload["verdict_transition"] == {
            "before": "BLOCK", "after": "BLOCK", "changed": False,
        }
        assert payload["scientific_validation"] is False
        assert payload["automatic_interpretation"] is False
        assert payload["scope_notice"]
        change, = payload["changes"]
        assert change["path"] == path
        assert change["after"] == proposed_value
        assert change["before_present"] is (field != "population")
    else:
        assert "Verdict: BLOCK -> BLOCK" in output
        assert path in output
    assert json.loads(before.read_text()) == review_baseline
    assert json.loads(after.read_text()) == proposed


def test_contract_diff_catches_reclassification_that_removes_multiplicity(review_baseline) -> None:
    proposed = deepcopy(review_baseline)
    proposed["claim"]["type"] = "descriptive"

    before_report = validate_contract(review_baseline)
    after_report = validate_contract(proposed)
    assert "CC205" in {finding.rule_id for finding in before_report.findings}
    assert "CC205" not in {finding.rule_id for finding in after_report.findings}
    diff = build_contract_diff(review_baseline, proposed)
    assert diff.before_verdict == diff.after_verdict == "BLOCK"
    assert [change.path for change in diff.changes] == ["claim.type"]


def test_contract_diff_preserves_types_inside_lists(review_baseline) -> None:
    before = deepcopy(review_baseline)
    after = deepcopy(review_baseline)
    before["review_metadata"] = [{"declared": True}]
    after["review_metadata"] = [{"declared": 1}]

    diff = build_contract_diff(before, after)

    assert diff.changed
    assert [change.path for change in diff.changes] == ["review_metadata"]


def test_cli_contract_diff_gate_accepts_reformatted_block(review_baseline, tmp_path, capsys) -> None:
    before = tmp_path / "baseline.json"
    after = tmp_path / "returned.yaml"
    before.write_text(json.dumps(review_baseline), encoding="utf-8")
    after.write_text(yaml.safe_dump(review_baseline, sort_keys=True), encoding="utf-8")

    assert main([
        "contract", "diff", str(before), str(after), "--fail-on-change", "--json",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict_transition"]["before"] == "BLOCK"
    assert payload["changes"] == []


def test_cli_contract_diff_gate_supports_stdin(review_baseline, tmp_path, capsys, monkeypatch) -> None:
    before = tmp_path / "baseline.json"
    before.write_text(json.dumps(review_baseline), encoding="utf-8")
    proposed = deepcopy(review_baseline)
    del proposed["claim"]["text"]
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(proposed)))

    assert main([
        "contract", "diff", str(before), "-", "--fail-on-change", "--json",
    ]) == 1
    change, = json.loads(capsys.readouterr().out)["changes"]
    assert change["path"] == "claim.text"
    assert change["after_present"] is False


@pytest.mark.parametrize("options", [[], ["--json"]])
def test_cli_contract_diff_gate_missing_input(tmp_path, capsys, options) -> None:
    assert main([
        "contract", "diff", str(tmp_path / "missing.json"),
        str(tmp_path / "also-missing.json"), "--fail-on-change", *options,
    ]) == 2
    captured = capsys.readouterr()
    if options:
        assert json.loads(captured.out)["error"]["code"] == "INPUT_ERROR"
    else:
        assert "Input error" in captured.err
