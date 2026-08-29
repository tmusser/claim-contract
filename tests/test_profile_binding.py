from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from claim_contract import (
    Report,
    Verdict,
    build_contract_binding,
    build_profile_manifest_binding,
    get_profile_manifest,
    load_contract,
    validate_contract,
)

ROOT = Path(__file__).parents[1]
CONTRACT_PATH = ROOT / "examples/descriptive_summary/contract.yaml"


def test_generated_bound_report_carries_current_profile_manifest_identity() -> None:
    contract = load_contract(CONTRACT_PATH)
    report = validate_contract(contract)
    payload = report.to_dict()

    assert report.profile_manifest_binding is not None
    serialized = payload["contract"]["profile_manifest_binding"]
    assert serialized == report.profile_manifest_binding.to_dict()
    assert serialized["algorithm"] == "sha256"
    assert serialized["canonicalization"] == "profile-manifest-semantics-v1"
    assert len(serialized["profile_manifest_sha256"]) == 64

    binding = report.resolved_profile_manifest_binding()
    assert binding is not None
    assert binding.matches_manifest(get_profile_manifest(report.profile).to_dict())


def test_profile_binding_is_captured_before_later_manifest_changes() -> None:
    report = validate_contract(load_contract(CONTRACT_PATH))
    captured = report.profile_manifest_binding
    assert captured is not None

    changed = deepcopy(get_profile_manifest(report.profile).to_dict())
    changed["rules"][0]["trigger"] += " Later mutation."

    assert captured != build_profile_manifest_binding(changed)
    assert report.to_dict()["contract"]["profile_manifest_binding"] == captured.to_dict()


def test_profile_binding_ignores_tool_release_metadata() -> None:
    manifest = get_profile_manifest("minimum-v0.1").to_dict()
    changed = deepcopy(manifest)
    changed["tool"]["version"] = "999.999.999"

    assert build_profile_manifest_binding(manifest) == build_profile_manifest_binding(changed)


def test_profile_binding_changes_when_rule_metadata_changes() -> None:
    manifest = get_profile_manifest("minimum-v0.1").to_dict()
    changed = deepcopy(manifest)
    changed["rules"][0]["known_boundary"] += " Changed boundary."

    assert build_profile_manifest_binding(manifest) != build_profile_manifest_binding(changed)


def test_profile_binding_changes_when_rule_order_changes() -> None:
    manifest = get_profile_manifest("minimum-v0.1").to_dict()
    changed = deepcopy(manifest)
    changed["rules"][0], changed["rules"][1] = changed["rules"][1], changed["rules"][0]

    assert build_profile_manifest_binding(manifest) != build_profile_manifest_binding(changed)


def test_unbound_manual_report_does_not_invent_profile_identity() -> None:
    report = Report(Verdict.READY, "minimum-v0.1", "Observed result.")

    assert report.resolved_profile_manifest_binding() is None
    assert "profile_manifest_binding" not in report.to_dict()["contract"]


def test_explicit_profile_binding_can_be_preserved_on_manual_bound_report() -> None:
    contract = load_contract(CONTRACT_PATH)
    manifest = get_profile_manifest("minimum-v0.1").to_dict()
    explicit = build_profile_manifest_binding(manifest)
    report = Report(
        verdict=Verdict.READY,
        profile="minimum-v0.1",
        claim_text="Observed result.",
        input_binding=build_contract_binding(contract),
        profile_manifest_binding=explicit,
    )

    assert report.resolved_profile_manifest_binding() == explicit
    assert report.to_dict()["contract"]["profile_manifest_binding"] == explicit.to_dict()
