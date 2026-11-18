"""Portable packet manifests preserve bytes and declared bindings across copies."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from claim_contract.cli import main
from claim_contract.io import load_contract
from claim_contract.packet_manifest import MANIFEST_NAME, create_manifest, verify_manifest
from claim_contract.validator import validate_contract


@pytest.fixture
def packet(tmp_path):
    folder = tmp_path / "original review"
    (folder / "contracts/team").mkdir(parents=True)
    (folder / "validate/team").mkdir(parents=True)
    (folder / "evidence").mkdir()
    contract = Path("examples/onboarding_conversion/contract.yaml")
    shutil.copyfile(contract, folder / "contracts/team/C01.yaml")
    report = validate_contract(load_contract(contract)).to_dict()
    (folder / "validate/team/C01.json").write_text(json.dumps(report), encoding="utf-8")
    (folder / "validate/team/C01.stderr").write_bytes(b"")
    (folder / "validate/team/C01.exit-code").write_text("1\n", encoding="utf-8")
    (folder / "evidence/plot data.bin").write_bytes(b"\x00\xff\x01")
    (folder / "task.md").write_text("Review requested.\n", encoding="utf-8")
    findings = "; ".join(
        f"{f['rule_id']}/{f['severity']}/{f['path']}" for f in report["findings"]
    ) or "-"
    (folder / "packet.md").write_text(
        "# Review\n\n[Evidence](evidence/plot%20data.bin)\n"
        "[External reference](https://example.invalid/source)\n\n"
        "## Validation summary\n\n"
        "| Contract | Claim text | Verdict | Findings | Report |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"| [C01](contracts/team/C01.yaml) | {report['claim_text']} | "
        f"{report['verdict']} | {findings} | [JSON](validate/team/C01.json) |\n",
        encoding="utf-8",
    )
    return folder


def _cli(folder, operation, capsys, *extra):
    code = main(["packet", "manifest", operation, str(folder), "--json", *extra])
    return code, json.loads(capsys.readouterr().out)


def _codes(payload):
    return {(item["code"], item.get("path")) for item in payload["failures"]}


def test_create_and_relocate(packet, tmp_path, capsys):
    code, result = _cli(packet, "create", capsys)
    assert code == 0
    manifest_path = packet / MANIFEST_NAME
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["scientific_validation"] is False
    assert saved["entrypoint"] == "packet.md"
    assert saved["type"] == "claim_contract.packet_manifest"
    assert "evidence/plot data.bin" in saved["artifacts"]
    assert saved["artifacts"]["evidence/plot data.bin"] == hashlib.sha256(b"\x00\xff\x01").hexdigest()
    assert MANIFEST_NAME not in saved["artifacts"]
    assert saved["contract_reports"][0]["contract"] == "contracts/team/C01.yaml"
    report = json.loads((packet / "validate/team/C01.json").read_text(encoding="utf-8"))
    assert saved["contract_reports"][0]["input_binding"] == report["contract"]["input_binding"]
    assert saved["contract_reports"][0]["profile_manifest_binding"] == report["contract"]["profile_manifest_binding"]
    assert result["manifest_sha256"] == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert str(packet) not in manifest_path.read_text(encoding="utf-8")
    destination = tmp_path / "another location" / "review"
    shutil.copytree(packet, destination)
    assert _cli(destination, "verify", capsys, "--expected-sha256", result["manifest_sha256"])[0] == 0


@pytest.mark.parametrize("relative", [
    "packet.md", "contracts/team/C01.yaml", "validate/team/C01.json", "evidence/plot data.bin",
])
def test_changed_artifact_is_identified(packet, capsys, relative):
    create_manifest(packet)
    with (packet / relative).open("ab") as stream:
        stream.write(b"\n")
    code, result = _cli(packet, "verify", capsys)
    assert code == 1
    assert ("MODIFIED_ARTIFACT", relative) in _codes(result)


def test_missing_and_extra_files_detected_together(packet, capsys):
    create_manifest(packet)
    (packet / "validate/team/C01.json").unlink()
    (packet / "evidence/unexpected.txt").touch()
    code, result = _cli(packet, "verify", capsys)
    assert code == 1
    assert ("MISSING_ARTIFACT", "validate/team/C01.json") in _codes(result)
    assert ("EXTRA_ARTIFACT", "evidence/unexpected.txt") in _codes(result)


def test_no_overwrite_and_no_verify_mutation(packet, capsys):
    create_manifest(packet)
    before = (packet / MANIFEST_NAME).read_bytes()
    assert _cli(packet, "create", capsys)[0] == 1
    assert _cli(packet, "verify", capsys)[0] == 0
    assert (packet / MANIFEST_NAME).read_bytes() == before


def test_external_manifest_digest_detects_rewritten_inventory(packet, capsys):
    original = create_manifest(packet)["manifest_sha256"]
    path = packet / MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8"))
    (packet / "task.md").write_text("Different task.", encoding="utf-8")
    manifest["artifacts"]["task.md"] = hashlib.sha256((packet / "task.md").read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_manifest(packet)["failures"] == []
    code, result = _cli(packet, "verify", capsys, "--expected-sha256", original)
    assert code == 1
    assert ("MANIFEST_DIGEST_MISMATCH", MANIFEST_NAME) in _codes(result)


def test_contract_report_metadata_cannot_silently_drift(packet, capsys):
    create_manifest(packet)
    path = packet / MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["contract_reports"][0]["report"] = "validate/other.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    code, result = _cli(packet, "verify", capsys)
    assert code == 1
    assert ("CONTRACT_REPORT_METADATA_MISMATCH", MANIFEST_NAME) in _codes(result)


def test_verify_does_not_rerun_validator(packet, monkeypatch):
    create_manifest(packet)

    def unexpected(*args, **kwargs):
        pytest.fail("Historical byte verification must not rerun current profile rules")

    monkeypatch.setattr("claim_contract.packet_manifest.verify_packet_consistency", unexpected)
    assert verify_manifest(packet)["failures"] == []


def test_creation_rejects_consistent_links_but_wrong_verdict(packet, capsys):
    path = packet / "packet.md"
    path.write_text(path.read_text(encoding="utf-8").replace(" | BLOCK | ", " | READY | "), encoding="utf-8")
    code, result = _cli(packet, "create", capsys)
    assert code == 1
    assert "VERDICT_MISMATCH" in result["failures"][0]["reason"]
    assert not (packet / MANIFEST_NAME).exists()


def test_creation_rejects_link_outside_directory(packet, tmp_path, capsys):
    (tmp_path / "outside.txt").write_text("outside", encoding="utf-8")
    with (packet / "packet.md").open("a", encoding="utf-8") as stream:
        stream.write("\n[Not bundled](../outside.txt)\n")
    code, result = _cli(packet, "create", capsys)
    assert code == 1
    assert "escapes packet" in result["failures"][0]["reason"]
    assert not (packet / MANIFEST_NAME).exists()


def test_symlinks_are_rejected(packet, tmp_path, capsys):
    outside = tmp_path / "outside.txt"
    outside.touch()
    try:
        (packet / "evidence/link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    code, result = _cli(packet, "create", capsys)
    assert code == 1
    assert "Symlink" in result["failures"][0]["reason"]


def test_duplicate_manifest_keys_fail_closed(packet, capsys):
    create_manifest(packet)
    path = packet / MANIFEST_NAME
    path.write_text('{"artifacts": {}, "artifacts": {}}', encoding="utf-8")
    code, result = _cli(packet, "verify", capsys)
    assert code == 1
    assert "Duplicate JSON field" in result["failures"][0]["reason"]


def test_missing_manifest_and_nonexistent_directory(packet, tmp_path, capsys):
    assert _cli(packet, "verify", capsys)[0] == 1
    assert _cli(tmp_path / "absent", "verify", capsys)[0] == 2
