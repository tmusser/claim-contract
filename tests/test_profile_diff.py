from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema

from claim_contract.cli import main
from claim_contract.profile_diff import build_profile_diff, load_profile_manifest
from claim_contract.profiles import DEFAULT_PROFILE, get_profile_manifest


ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "schemas/profile-diff-v1.schema.json"


def _manifest() -> dict:
    return copy.deepcopy(get_profile_manifest(DEFAULT_PROFILE).to_dict())


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_profile_diff_schema_is_valid_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_tool_metadata_change_is_not_semantic_profile_drift() -> None:
    before = _manifest()
    after = _manifest()
    after["tool"]["version"] = "99.0.0"

    diff = build_profile_diff(before, after)

    assert diff.semantic_changed is False
    assert diff.tool_metadata_changed is True
    assert diff.change_count == 0
    assert diff.before_binding == diff.after_binding
    assert diff.profile_changes == ()
    assert diff.rules_added == ()
    assert diff.rules_removed == ()
    assert diff.rules_changed == ()
    assert diff.rule_order_changed is False


def test_profile_diff_reports_rule_add_remove_and_field_changes() -> None:
    before = _manifest()
    after = _manifest()

    after["rules"] = [rule for rule in after["rules"] if rule["id"] != "CC101"]
    cc203 = next(rule for rule in after["rules"] if rule["id"] == "CC203")
    cc203["severity"] = "BLOCK"
    cc203["consumed_fields"] = [*cc203["consumed_fields"], "evidence.design"]
    cc203["trigger"] = "Changed trigger text."
    cc203["known_boundary"] = "Changed boundary text."
    after["rules"].append(
        {
            "id": "CC999",
            "severity": "REVIEW",
            "consumed_fields": ["claim.text"],
            "trigger": "Synthetic added rule for diff testing.",
            "known_boundary": "Synthetic boundary for diff testing.",
        }
    )
    after["rule_count"] = len(after["rules"])

    diff = build_profile_diff(before, after)
    payload = diff.to_dict()

    assert diff.semantic_changed is True
    assert [rule["id"] for rule in payload["rules_added"]] == ["CC999"]
    assert [rule["id"] for rule in payload["rules_removed"]] == ["CC101"]
    assert [rule["id"] for rule in payload["rules_changed"]] == ["CC203"]
    assert [
        change["field"] for change in payload["rules_changed"][0]["changes"]
    ] == ["severity", "consumed_fields", "trigger", "known_boundary"]
    assert payload["automatic_compatibility_classification"] is False
    assert "breaking" in payload["scope_notice"].lower()


def test_profile_diff_reports_profile_metadata_and_pure_rule_reordering() -> None:
    before = _manifest()
    after = _manifest()
    after["profile"]["description"] = "Revised profile description."
    after["not_evaluated"] = [*after["not_evaluated"], "a newly declared boundary"]
    after["rules"][0], after["rules"][1] = after["rules"][1], after["rules"][0]

    diff = build_profile_diff(before, after)
    payload = diff.to_dict()

    assert payload["semantic_changed"] is True
    assert [item["path"] for item in payload["profile_changes"]] == [
        "profile.description",
        "not_evaluated",
    ]
    assert payload["rule_order"]["changed"] is True
    assert payload["rule_order"]["before"][:2] == ["CC001", "CC101"]
    assert payload["rule_order"]["after"][:2] == ["CC101", "CC001"]
    assert payload["change_count"] == 3


def test_semantic_change_flag_matches_profile_binding_identity() -> None:
    before = _manifest()
    variants = []

    tool_only = _manifest()
    tool_only["tool"]["version"] = "2.0.0"
    variants.append(tool_only)

    description = _manifest()
    description["profile"]["description"] = "changed"
    variants.append(description)

    severity = _manifest()
    severity["rules"][0]["severity"] = "REVIEW"
    variants.append(severity)

    reordered = _manifest()
    reordered["rules"][0], reordered["rules"][1] = (
        reordered["rules"][1],
        reordered["rules"][0],
    )
    variants.append(reordered)

    for after in variants:
        diff = build_profile_diff(before, after)
        assert diff.semantic_changed is (diff.before_binding != diff.after_binding)


def test_profile_manifest_loader_rejects_duplicate_rule_ids(tmp_path: Path) -> None:
    payload = _manifest()
    payload["rules"].append(copy.deepcopy(payload["rules"][0]))
    payload["rule_count"] = len(payload["rules"])
    path = tmp_path / "duplicate.json"
    _write(path, payload)

    try:
        load_profile_manifest(path)
    except ValueError as exc:
        assert "Duplicate profile manifest rule id" in str(exc)
    else:
        raise AssertionError("duplicate rule IDs must be rejected")


def test_cli_profile_diff_json_and_schema(capsys, tmp_path: Path) -> None:
    before = _manifest()
    after = _manifest()
    after["rules"][0]["severity"] = "REVIEW"
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    _write(before_path, before)
    _write(after_path, after)

    code = main(["profile", "diff", str(before_path), str(after_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert captured.err == ""
    assert payload["type"] == "claim_contract.profile_diff"
    assert payload["schema_version"] == "1.0"
    assert payload["semantic_changed"] is True
    assert payload["rules_changed"][0]["id"] == "CC001"
    jsonschema.validate(payload, _schema())


def test_cli_profile_diff_text_is_mechanical_not_compatibility_judgment(
    capsys, tmp_path: Path
) -> None:
    before = _manifest()
    after = _manifest()
    after["rules"][0]["trigger"] = "Changed trigger."
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    _write(before_path, before)
    _write(after_path, after)

    code = main(["profile", "diff", str(before_path), str(after_path)])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    assert "Semantic profile changed: true" in captured.out
    assert "Automatic compatibility classification: false" in captured.out
    assert "CC001" in captured.out
    assert "trigger" in captured.out


def test_cli_profile_diff_json_input_error_uses_existing_error_envelope(
    capsys, tmp_path: Path
) -> None:
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    before_path.write_text("[]", encoding="utf-8")
    _write(after_path, _manifest())

    code = main(["profile", "diff", str(before_path), str(after_path), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["type"] == "claim_contract.error"
    assert "root must be an object" in payload["error"]["message"].lower()
