from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_contract(path: str | Path) -> dict[str, Any]:
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
