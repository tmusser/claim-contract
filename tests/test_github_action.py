from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
ACTION = ROOT / "action.yml"


def test_action_metadata_is_minimal_and_delegates_to_existing_cli() -> None:
    payload = yaml.safe_load(ACTION.read_text(encoding="utf-8"))

    assert payload["name"] == "claim-contract"
    assert payload["inputs"]["contract"]["required"] is True
    assert payload["inputs"]["warnings-as-errors"]["required"] is False
    assert payload["inputs"]["warnings-as-errors"]["default"] == "false"
    assert payload["runs"]["using"] == "composite"

    rendered = ACTION.read_text(encoding="utf-8")
    assert "uses: actions/setup-python@v5" in rendered
    assert 'python -m pip install "${{ github.action_path }}"' in rendered
    assert 'args=(validate "$CLAIM_CONTRACT_PATH")' in rendered
    assert 'args+=(--warnings-as-errors)' in rendered
    assert 'claim-contract "${args[@]}"' in rendered


def test_action_does_not_implement_a_second_verdict_classifier() -> None:
    rendered = ACTION.read_text(encoding="utf-8")

    assert "READY)" not in rendered
    assert "REVIEW)" not in rendered
    assert "BLOCK)" not in rendered
    assert "scientific_validation" not in rendered
    assert "scope_notice" not in rendered
