from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "claims" / "ledger.yaml"
SCHEMA_PATH = ROOT / "schemas" / "claim-ledger-v1.1.schema.json"
LEGACY_SCHEMA_PATH = ROOT / "schemas" / "claim-ledger-v1.schema.json"


def _load_ledger() -> dict[str, object]:
    value = yaml.safe_load(LEDGER_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _load_schema(path: Path = SCHEMA_PATH) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_live_claim_ledger_matches_published_schema() -> None:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(_load_ledger())


def test_legacy_claim_ledger_schema_remains_published() -> None:
    schema = _load_schema(LEGACY_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)


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


def test_live_claims_preserve_creation_provenance() -> None:
    ledger = _load_ledger()
    assert ledger["schema_version"] == "1.1"

    claims = ledger["claims"]
    assert isinstance(claims, list)

    for claim in claims:
        provenance = claim["provenance"]
        assert isinstance(provenance, dict)
        assert provenance["recorded_at"]
        assert provenance["origin_refs"]

        context = provenance["context_snapshot"]
        assert isinstance(context, dict)
        revision = context["repository_revision"]
        assert isinstance(revision, str)
        assert len(revision) == 40
        assert context["refs"]
        assert context["note"]

        if provenance["generated_at"] is None:
            assert "not retained" in context["note"].lower()
