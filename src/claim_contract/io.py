from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


def _load_stdin_contract() -> dict[str, Any]:
    text = sys.stdin.read()
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Contract from stdin is not valid YAML or JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError("Contract root must be an object/mapping.")
    return value


def load_contract(path: str | Path) -> dict[str, Any]:
    if str(path) == "-":
        return _load_stdin_contract()

    contract_path = Path(path)
    if not contract_path.exists():
        raise FileNotFoundError(f"Contract file not found: {contract_path}")

    text = contract_path.read_text(encoding="utf-8")
    suffix = contract_path.suffix.lower()

    if suffix == ".json":
        value = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        value = yaml.safe_load(text)
    else:
        raise ValueError("Contract must be YAML (.yaml/.yml) or JSON (.json).")

    if not isinstance(value, dict):
        raise ValueError("Contract root must be an object/mapping.")
    return value
