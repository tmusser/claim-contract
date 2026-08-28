from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

from claim_contract.cli import main

ROOT = Path(__file__).parents[1]
LEDGER_PATH = ROOT / "claims/ledger.yaml"
SCHEMA_PATH = ROOT / "schemas/ledger-inspection-v1.schema.json"


def _ledger() -> dict:
    value = yaml.safe_load(LEDGER_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_ledger_inspection_schema_is_valid_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_ledger_list_json_filters_recorded_status_without_rewriting(capsys) -> None:
    source = _ledger()
    expected = [claim for claim in source["claims"] if claim["status"] == "OPEN"]

    code = main(["ledger", "list", str(LEDGER_PATH), "--status", "OPEN", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["type"] == "claim_contract.ledger_inspection"
    assert payload["inspection"] == {
        "automatic_adjudication": False,
        "claim_id": None,
        "mode": "list",
        "mutates_ledger": False,
        "notice": (
            "Inspection exposes recorded ledger fields only. It does not evaluate support_if, "
            "refute_if, evidence, or whether any status should change, and it does not mutate "
            "the ledger."
        ),
        "status_filter": "OPEN",
    }
    assert payload["ledger"] == {
        "schema_version": source["schema_version"],
        "type": source["type"],
        "scope_notice": source["scope_notice"],
    }
    assert payload["count"] == len(expected)
    assert payload["claims"] == expected
    jsonschema.validate(payload, _schema())


def test_ledger_show_json_returns_exact_recorded_claim(capsys) -> None:
    source = _ledger()
    expected = next(claim for claim in source["claims"] if claim["id"] == "CCL-002")

    code = main(["ledger", "show", "CCL-002", str(LEDGER_PATH), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["inspection"]["mode"] == "show"
    assert payload["inspection"]["claim_id"] == "CCL-002"
    assert payload["inspection"]["status_filter"] is None
    assert payload["inspection"]["automatic_adjudication"] is False
    assert payload["count"] == 1
    assert payload["claims"] == [expected]
    assert payload["claims"][0]["judge_contract"] == expected["judge_contract"]
    jsonschema.validate(payload, _schema())


def test_ledger_commands_default_to_repository_ledger(monkeypatch, capsys) -> None:
    monkeypatch.chdir(ROOT)

    code = main(["ledger", "show", "CCL-002", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["claims"][0]["id"] == "CCL-002"


def test_ledger_list_text_is_status_index_not_judgment(capsys) -> None:
    code = main(["ledger", "list", str(LEDGER_PATH), "--status", "OPEN"])
    output = capsys.readouterr().out

    assert code == 0
    assert "Automatic adjudication: false" in output
    assert "CCL-001 OPEN" in output
    assert "Support if (recorded, not evaluated)" not in output
    assert "Refute if (recorded, not evaluated)" not in output


def test_ledger_show_text_labels_judge_contract_as_not_evaluated(capsys) -> None:
    code = main(["ledger", "show", "CCL-002", str(LEDGER_PATH)])
    output = capsys.readouterr().out

    assert code == 0
    assert "CCL-002 OPEN" in output
    assert "Automatic adjudication: false" in output
    assert "Support if (recorded, not evaluated):" in output
    assert "Refute if (recorded, not evaluated):" in output


def test_ledger_status_filter_uses_recorded_status_only(tmp_path: Path, capsys) -> None:
    source = _ledger()
    changed = yaml.safe_load(yaml.safe_dump(source, sort_keys=False))
    target = next(claim for claim in changed["claims"] if claim["id"] == "CCL-003")
    target["status"] = "RETIRED"
    temp_ledger = tmp_path / "ledger.yaml"
    temp_ledger.write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")

    code = main(
        ["ledger", "list", str(temp_ledger), "--status", "RETIRED", "--format", "json"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["count"] == 1
    assert payload["claims"][0] == target
    assert payload["claims"][0]["status"] == "RETIRED"


def test_ledger_list_does_not_mutate_source_file(capsys) -> None:
    before = LEDGER_PATH.read_text(encoding="utf-8")

    code = main(["ledger", "list", str(LEDGER_PATH), "--json"])
    capsys.readouterr()

    assert code == 0
    assert LEDGER_PATH.read_text(encoding="utf-8") == before


def test_ledger_show_unknown_claim_is_input_error(capsys) -> None:
    code = main(["ledger", "show", "CCL-999", str(LEDGER_PATH), "--json"])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.out == ""
    assert "Ledger claim not found: CCL-999" in captured.err


def test_ledger_list_rejects_unknown_status(capsys) -> None:
    code = main(["ledger", "list", str(LEDGER_PATH), "--status", "PROVEN", "--json"])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.out == ""
    assert "Unsupported ledger status 'PROVEN'" in captured.err
