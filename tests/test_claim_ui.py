from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from claim_contract.claim_ui import (
    PROVENANCE_SCOPE_NOTICE,
    build_claim_ui_bundle,
    load_claim_provenance,
)
from claim_contract.cli import main


ROOT = Path(__file__).parents[1]
LEDGER = ROOT / "claims" / "ledger.yaml"
GRAPH = ROOT / "claims" / "graph.yaml"
PROVENANCE = ROOT / "claims" / "provenance.yaml"
PROVENANCE_SCHEMA = ROOT / "schemas" / "claim-provenance-v1.schema.json"
BUNDLE_SCHEMA = ROOT / "schemas" / "claim-ui-bundle-v1.schema.json"


def _schema(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_provenance(tmp_path: Path, claims: list[dict]) -> Path:
    path = tmp_path / "provenance.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "type": "claim_contract.claim_provenance",
                "scope_notice": PROVENANCE_SCOPE_NOTICE,
                "claims": claims,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_claim_ui_schemas_are_valid_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema(PROVENANCE_SCHEMA))
    jsonschema.Draft202012Validator.check_schema(_schema(BUNDLE_SCHEMA))


def test_checked_in_provenance_sidecar_matches_schema() -> None:
    payload = yaml.safe_load(PROVENANCE.read_text(encoding="utf-8"))
    jsonschema.validate(payload, _schema(PROVENANCE_SCHEMA))


def test_bundle_uses_ledger_time_and_existing_file_provenance() -> None:
    bundle = build_claim_ui_bundle(
        ledger_path=LEDGER,
        graph_path=GRAPH,
        provenance_path=PROVENANCE,
    )
    jsonschema.validate(bundle, _schema(BUNDLE_SCHEMA))

    claims = {claim["id"]: claim for claim in bundle["claims"]}
    ccl001 = claims["CCL-001"]

    assert ccl001["logged_at"] == "2026-07-27T20:07:34Z"
    assert ccl001["classification"] == "ROOT"
    assert ccl001["is_root"] is True
    files = {item["ref"]: item for item in ccl001["source_files"]}
    assert "docs/MACHINE_READABLE.md" in files
    assert set(files["docs/MACHINE_READABLE.md"]["roles"]) == {
        "creation_context",
        "current_evidence",
    }
    assert ccl001["data_sources"] == []
    assert bundle["scientific_validation"] is False
    assert bundle["automatic_adjudication"] is False
    assert bundle["read_only"] is True


def test_optional_sidecar_adds_file_and_database_query_lineage(tmp_path: Path) -> None:
    provenance_path = _write_provenance(
        tmp_path,
        [
            {
                "claim_id": "CCL-001",
                "note": "Explicit lineage retained for claim-map inspection.",
                "source_files": [
                    {
                        "ref": "analysis/ccl001.md",
                        "role": "analysis",
                        "note": "Declared analysis source.",
                    }
                ],
                "data_sources": [
                    {
                        "system": "athena",
                        "catalog": "AwsDataCatalog",
                        "database": "analytics",
                        "table": "funnel_events",
                        "query": {
                            "ref": "queries/ccl001.sql",
                            "text": "SELECT segment, COUNT(*) FROM analytics.funnel_events GROUP BY 1",
                        },
                    }
                ],
            }
        ],
    )

    bundle = build_claim_ui_bundle(
        ledger_path=LEDGER,
        graph_path=GRAPH,
        provenance_path=provenance_path,
    )
    jsonschema.validate(bundle, _schema(BUNDLE_SCHEMA))

    ccl001 = next(claim for claim in bundle["claims"] if claim["id"] == "CCL-001")
    source = next(
        item for item in ccl001["source_files"]
        if item["ref"] == "analysis/ccl001.md"
    )
    assert source["roles"] == ["analysis"]
    lineage = ccl001["data_sources"][0]
    assert lineage["system"] == "athena"
    assert lineage["database"] == "analytics"
    assert lineage["table"] == "funnel_events"
    assert lineage["query"]["ref"] == "queries/ccl001.sql"
    assert lineage["query"]["text"].startswith("SELECT segment")
    assert ccl001["provenance_note"] == (
        "Explicit lineage retained for claim-map inspection."
    )


def test_provenance_rejects_malformed_claim_id(tmp_path: Path) -> None:
    provenance_path = _write_provenance(
        tmp_path,
        [
            {
                "claim_id": "claim-1",
                "source_files": [],
                "data_sources": [],
            }
        ],
    )

    with pytest.raises(ValueError, match="must match CCL-###"):
        load_claim_provenance(provenance_path)


def test_provenance_rejects_unknown_claim_id(tmp_path: Path) -> None:
    provenance_path = _write_provenance(
        tmp_path,
        [
            {
                "claim_id": "CCL-999",
                "source_files": [],
                "data_sources": [],
            }
        ],
    )

    with pytest.raises(ValueError, match="unknown ledger claim"):
        build_claim_ui_bundle(
            ledger_path=LEDGER,
            graph_path=GRAPH,
            provenance_path=provenance_path,
        )


def test_provenance_query_requires_text_or_ref(tmp_path: Path) -> None:
    provenance_path = _write_provenance(
        tmp_path,
        [
            {
                "claim_id": "CCL-001",
                "source_files": [],
                "data_sources": [
                    {
                        "system": "athena",
                        "table": "funnel_events",
                        "query": {},
                    }
                ],
            }
        ],
    )

    with pytest.raises(ValueError, match="query requires ref or text"):
        load_claim_provenance(provenance_path)


def test_ui_export_cli_writes_static_bundle(tmp_path: Path, capsys) -> None:
    output = tmp_path / "claim-map.json"

    code = main(
        [
            "ui",
            "export",
            "--ledger",
            str(LEDGER),
            "--graph",
            str(GRAPH),
            "--provenance",
            str(PROVENANCE),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    assert "Read only: true" in captured.out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["type"] == "claim_contract.claim_ui_bundle"
    assert len(payload["claims"]) == 3
    jsonschema.validate(payload, _schema(BUNDLE_SCHEMA))


def test_bundle_can_omit_optional_provenance_sidecar() -> None:
    bundle = build_claim_ui_bundle(
        ledger_path=LEDGER,
        graph_path=GRAPH,
        provenance_path=None,
    )

    assert bundle["generated_from"]["provenance"] is None
    assert all(claim["data_sources"] == [] for claim in bundle["claims"])
