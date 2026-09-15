from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from claim_contract.claim_graph import analyze_claim_graph


def test_live_prune_report_matches_published_schema() -> None:
    report = analyze_claim_graph("claims/ledger.yaml", "claims/graph.yaml").to_dict()
    schema = json.loads(
        Path("schemas/claim-graph-prune-report-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(report)
    assert report["counts"]["prune_candidates"] == 0
    assert report["automatic_retirement"] is False
    assert report["mutates_ledger"] is False
