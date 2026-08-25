from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import jsonschema

from claim_contract import get_profile_manifest, load_contract, validate_contract
from claim_contract.cli import main
from claim_contract.profiles import DEFAULT_PROFILE
import claim_contract.validator as validator_module

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "schemas/profile-manifest-v1.schema.json"
RULES_DOC = ROOT / "docs/RULES.md"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _manifest():
    return get_profile_manifest(DEFAULT_PROFILE)


def test_profile_manifest_schema_is_valid_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_minimum_profile_manifest_matches_published_schema() -> None:
    payload = _manifest().to_dict()

    jsonschema.validate(payload, _schema())
    assert payload["type"] == "claim_contract.profile_manifest"
    assert payload["schema_version"] == "1.0"
    assert payload["profile"]["name"] == "minimum-v0.1"
    assert payload["profile"]["contract_schema"] == (
        "schemas/contract-minimum-v0.1.schema.json"
    )
    assert payload["scientific_validation"] is False
    assert payload["rule_count"] == len(payload["rules"]) == 14


def test_profile_manifest_rule_ids_are_unique_and_complete() -> None:
    rules = _manifest().rules
    ids = [rule.rule_id for rule in rules]

    assert len(ids) == len(set(ids))
    assert ids == [
        "CC001",
        "CC101",
        "CC102",
        "CC201",
        "CC202",
        "CC203",
        "CC204",
        "CC205",
        "CC206",
        "CC301",
        "CC302",
        "CC303",
        "CC304",
        "CC305",
    ]
    assert all(rule.consumed_fields for rule in rules)
    assert all(rule.trigger for rule in rules)
    assert all(rule.known_boundary for rule in rules)


def test_validator_rule_ids_are_registered_in_manifest() -> None:
    source = inspect.getsource(validator_module.validate_contract)
    executable_rule_ids = set(re.findall(r'"(CC[0-9]{3})"', source))
    manifest_rule_ids = {rule.rule_id for rule in _manifest().rules}

    assert executable_rule_ids == manifest_rule_ids


def test_human_rule_table_ids_and_severities_match_manifest() -> None:
    documented: dict[str, str] = {}
    for line in RULES_DOC.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\| (CC[0-9]{3}) \| (REVIEW|BLOCK) \|", line)
        if match:
            documented[match.group(1)] = match.group(2)

    registered = {
        rule.rule_id: rule.severity.value
        for rule in _manifest().rules
    }
    assert documented == registered


def test_example_findings_use_registered_severities() -> None:
    manifest = _manifest()
    for contract_path in sorted((ROOT / "examples").rglob("contract.yaml")):
        report = validate_contract(load_contract(contract_path))
        for finding in report.findings:
            assert finding.severity is manifest.rule(finding.rule_id).severity


def test_cli_profile_show_json_is_machine_readable(capsys) -> None:
    code = main(["profile", "show", "minimum-v0.1", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert captured.err == ""
    assert payload == _manifest().to_dict()
    jsonschema.validate(payload, _schema())


def test_cli_profile_show_text_includes_rule_metadata(capsys) -> None:
    code = main(["profile", "show", "minimum-v0.1"])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    assert "Profile: minimum-v0.1" in captured.out
    assert "Rules: 14" in captured.out
    assert "CC301 BLOCK" in captured.out
    assert "Trigger:" in captured.out
    assert "Consumes:" in captured.out
    assert "Boundary:" in captured.out


def test_cli_profile_show_rejects_unknown_profile(capsys) -> None:
    code = main(["profile", "show", "future-profile", "--json"])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.out == ""
    assert "Unsupported profile" in captured.err
