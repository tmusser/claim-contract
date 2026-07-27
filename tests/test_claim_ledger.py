from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "claims" / "ledger.yaml"
SCHEMA_PATH = ROOT / "schemas" / "claim-ledger-v1.schema.json"


def _load_ledger() -> dict[str, object]:
    value = yaml.safe_load(LEDGER_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _load_schema() -> dict[str, object]:
    value = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_live_claim_ledger_matches_published_schema() -> None:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_load_ledger())


def test_claim_ids_are_unique_and_open_claims_are_unjudged() -> None:
    ledger = _load_ledger()
    claims = ledger["claims"]
    assert isinstance(claims, list)

    ids = [claim["id"] for claim in claims]
    assert len(ids) == len(set(ids))

    for claim in claims:
        assert isinstance(claim, dict)
        if claim["status"] != "OPEN":
            continue

        judgment = claim["judgment"]
        assert judgment == {
            "last_evaluated": None,
            "judged_by": None,
            "evidence_refs": [],
            "note": None,
        }
