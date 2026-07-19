from __future__ import annotations

import json
from pathlib import Path

import pytest

from claim_contract.cli import main
from claim_contract.metadata import TOOL_NAME, TOOL_VERSION

ROOT = Path(__file__).parents[1]


def test_cli_ready_json_preserves_scope(capsys) -> None:
    code = main(
        [
            "validate",
            str(ROOT / "examples/descriptive_summary/contract.yaml"),
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "READY"
    assert payload["scientific_validation"] is False
    assert "not scientific validation" in payload["scope_notice"].lower()
    assert payload["not_evaluated"]


def test_cli_block_exit_code(capsys) -> None:
    code = main(["validate", str(ROOT / "examples/onboarding_conversion/contract.yaml")])
    assert code == 1
    assert "Verdict: BLOCK" in capsys.readouterr().out


def test_cli_json_alias(capsys) -> None:
    code = main(
        [
            "validate",
            str(ROOT / "examples/descriptive_summary/contract.yaml"),
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "READY"
    assert payload["scientific_validation"] is False


def test_cli_version_uses_package_metadata(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"{TOOL_NAME} {TOOL_VERSION}"
