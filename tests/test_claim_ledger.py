from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "claims" / "ledger.yaml"
SCHEMA_PATH = ROOT / "schemas" / "claim-ledger-v1.2.schema.json"
LEGACY_SCHEMA_PATHS = (
    ROOT / "schemas" / "claim-ledger-v1.schema.json",
    ROOT / "schemas" / "claim-ledger-v1.1.schema.json",
)


def _load_ledger() -> dict[str, object]:
    value = yaml.safe_load(LEDGER_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _load_schema(path: Path = SCHEMA_PATH) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_load_schema(), format_checker=FormatChecker())


def test_live_claim_ledger_matches_published_schema() -> None:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    _validator().validate(_load_ledger())


def test_historical_claim_ledger_schemas_remain_published() -> None:
    for path in LEGACY_SCHEMA_PATHS:
        schema = _load_schema(path)
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
            "evidence_snapshot": None,
            "note": None,
        }


def test_live_claims_preserve_creation_provenance() -> None:
    ledger = _load_ledger()
    assert ledger["schema_version"] == "1.2"

    claims = ledger["claims"]
    assert isinstance(claims, list)

    for claim in claims:
        provenance = claim["provenance"]
        assert isinstance(provenance, dict)
        assert provenance["recorded_at"]
        assert provenance["record_ref"]
        assert isinstance(provenance["origin_refs"], list)

        context = provenance["context_snapshot"]
        assert isinstance(context, dict)
        revision = context["repository_revision"]
        assert isinstance(revision, str)
        assert len(revision) == 40
        assert context["refs"]
        assert context["note"]

        if provenance["generated_at"] is None:
            assert "not retained" in context["note"].lower()


def _adjudicated_ledger(status: str = "SUPPORT_MET") -> dict[str, object]:
    ledger = deepcopy(_load_ledger())
    claim = ledger["claims"][0]
    claim["status"] = status
    claim["judgment"] = {
        "last_evaluated": "2026-09-06T14:00:00Z",
        "judged_by": "independent-reviewer",
        "evidence_refs": ["README.md"],
        "evidence_snapshot": {
            "repository_revision": "0c2cea01537cf90dcc224614f2e35d4e1b2916fb",
            "refs": ["README.md"],
            "note": "Frozen repository evidence used for this bounded adjudication.",
        },
        "note": "Recorded judgment under the frozen judge contract.",
    }
    return ledger


@pytest.mark.parametrize("status", ["SUPPORT_MET", "REFUTE_MET", "INCONCLUSIVE"])
def test_adjudicated_status_requires_frozen_judgment_provenance(status: str) -> None:
    _validator().validate(_adjudicated_ledger(status))


def test_adjudicated_status_rejects_missing_evidence_snapshot() -> None:
    ledger = _adjudicated_ledger()
    ledger["claims"][0]["judgment"]["evidence_snapshot"] = None

    with pytest.raises(ValidationError):
        _validator().validate(ledger)


def test_open_status_cannot_carry_completed_judgment() -> None:
    ledger = _adjudicated_ledger()
    ledger["claims"][0]["status"] = "OPEN"

    with pytest.raises(ValidationError):
        _validator().validate(ledger)


def test_retired_status_may_remain_unjudged() -> None:
    ledger = deepcopy(_load_ledger())
    ledger["claims"][0]["status"] = "RETIRED"

    _validator().validate(ledger)
