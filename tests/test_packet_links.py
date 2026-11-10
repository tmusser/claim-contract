import json

import pytest

from claim_contract.cli import main
from claim_contract.metadata import TOOL_NAME, TOOL_VERSION


SCOPE_NOTICE = "Link integrity only. This does not validate any claim, contract, or evidence."


def test_packet_links_resolve(tmp_path, capsys):
    folder = tmp_path / "packet"
    folder.mkdir()
    (folder / "contract.yaml").write_text("synthetic", encoding="utf-8")
    (folder / "result.json").write_text("{}", encoding="utf-8")
    (folder / "image.svg").touch()
    packet = folder / "review.md"
    packet.write_text(
        '[Contract](contract.yaml) [Result](result.json#summary)\n'
        '![Image](<image.svg> "Preview")\n',
        encoding="utf-8",
    )

    assert main(["packet", "check", str(packet), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["failures"] == []
    assert payload["scope_notice"] == SCOPE_NOTICE
    assert payload["tool"] == {"name": TOOL_NAME, "version": TOOL_VERSION}


def test_packet_missing_contract(tmp_path, capsys):
    packet = tmp_path / "review.md"
    packet.write_text("# Packet\n\n[Contract](missing.yaml)\n", encoding="utf-8")

    assert main(["packet", "check", str(packet)]) == 1
    output = capsys.readouterr().out
    assert "Line 3: missing.yaml" in output
    assert SCOPE_NOTICE in output


def test_packet_ignores_https_and_anchor(tmp_path):
    packet = tmp_path / "review.md"
    packet.write_text("[External](https://example.invalid/file.json) [Top](#top)", encoding="utf-8")

    assert main(["packet", "check", str(packet)]) == 0


def test_packet_percent_encoded_space(tmp_path):
    (tmp_path / "two words.yaml").touch()
    packet = tmp_path / "review.md"
    packet.write_text("[Contract](two%20words.yaml)", encoding="utf-8")

    assert main(["packet", "check", str(packet)]) == 0


def test_packet_absolute_target(tmp_path, capsys):
    contract = tmp_path / "contract.yaml"
    contract.touch()
    packet = tmp_path / "review.md"
    packet.write_text(f"[Contract](<{contract.as_posix()}>)", encoding="utf-8")

    assert main(["packet", "check", str(packet)]) == 1
    assert f"Line 1: {contract.as_posix()} (Absolute filesystem target)" in capsys.readouterr().out


@pytest.mark.parametrize("content", ["{", "NaN"])
def test_packet_invalid_json(tmp_path, capsys, content):
    (tmp_path / "result.json").write_text(content, encoding="utf-8")
    packet = tmp_path / "review.md"
    packet.write_text("\n[Result](result.json)", encoding="utf-8")

    assert main(["packet", "check", str(packet), "--format", "json"]) == 1
    failure, = json.loads(capsys.readouterr().out)["failures"]
    assert failure["line"] == 2
    assert failure["target"] == "result.json"
    assert "invalid JSON" in failure["reason"]


@pytest.mark.parametrize("options", [[], ["--json"]])
def test_packet_missing_input(tmp_path, capsys, options):
    assert main(["packet", "check", str(tmp_path / "missing.md"), *options]) == 2
    captured = capsys.readouterr()
    if options:
        payload = json.loads(captured.out)
        assert payload["scope_notice"] == SCOPE_NOTICE
        assert "missing.md" in payload["error"]["message"]
    else:
        assert SCOPE_NOTICE in captured.err
        assert "missing.md" in captured.err
