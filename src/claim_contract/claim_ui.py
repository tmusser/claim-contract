"""Read-only claim-map bundle export for the optional React UI."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .claim_graph import (
    DEFAULT_GRAPH_PATH,
    GRAPH_SCOPE_NOTICE,
    analyze_claim_graph,
    load_claim_graph,
)
from .ledger import inspect_ledger


UI_BUNDLE_SCHEMA_VERSION = "1.0"
UI_BUNDLE_TYPE = "claim_contract.claim_ui_bundle"
UI_SCOPE_NOTICE = (
    "The claim map UI visualizes declared graph, ledger, and provenance metadata only. "
    "It does not verify evidence, execute queries, adjudicate claims, or mutate source artifacts."
)

PROVENANCE_SCHEMA_VERSION = "1.0"
PROVENANCE_TYPE = "claim_contract.claim_provenance"
PROVENANCE_SCOPE_NOTICE = (
    "Claim provenance records declared source and data-lineage metadata only. It does not "
    "verify that a file, table, or query supports, proves, or generated the claim."
)

DEFAULT_LEDGER_PATH = "claims/ledger.yaml"
DEFAULT_PROVENANCE_PATH = "claims/provenance.yaml"
DEFAULT_UI_BUNDLE_PATH = "ui/public/claim-map.json"


def load_claim_provenance(path: str | Path) -> dict[str, Any]:
    provenance_path = Path(path)
    if not provenance_path.exists():
        raise FileNotFoundError(f"Claim provenance file not found: {provenance_path}")

    value = yaml.safe_load(provenance_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Claim provenance root must be an object/mapping.")
    if value.get("schema_version") != PROVENANCE_SCHEMA_VERSION:
        raise ValueError(
            f"Claim provenance schema_version must be {PROVENANCE_SCHEMA_VERSION!r}."
        )
    if value.get("type") != PROVENANCE_TYPE:
        raise ValueError(f"Claim provenance type must be {PROVENANCE_TYPE!r}.")
    if value.get("scope_notice") != PROVENANCE_SCOPE_NOTICE:
        raise ValueError("Claim provenance scope_notice does not match the v1 contract.")

    claims = value.get("claims")
    if not isinstance(claims, list):
        raise ValueError("Claim provenance claims must be a list.")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(claims):
        if not isinstance(item, dict):
            raise ValueError(f"Claim provenance entry {index} must be an object/mapping.")
        allowed = {"claim_id", "source_files", "data_sources", "note"}
        unknown = set(item) - allowed
        if unknown:
            raise ValueError(
                f"Claim provenance entry {index} has unsupported field(s): "
                + ", ".join(sorted(unknown))
            )

        claim_id = item.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError(f"Claim provenance entry {index} requires claim_id.")
        claim_id = claim_id.strip()
        if claim_id in seen:
            raise ValueError(f"Claim provenance contains duplicate claim_id: {claim_id}")
        seen.add(claim_id)

        source_files = _normalize_source_files(item.get("source_files"), claim_id)
        data_sources = _normalize_data_sources(item.get("data_sources"), claim_id)
        note = item.get("note")
        if note is not None and (not isinstance(note, str) or not note.strip()):
            raise ValueError(f"Claim provenance {claim_id} note must be a non-empty string.")

        normalized.append(
            {
                "claim_id": claim_id,
                "source_files": source_files,
                "data_sources": data_sources,
                **({"note": note.strip()} if isinstance(note, str) else {}),
            }
        )

    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "type": PROVENANCE_TYPE,
        "scope_notice": PROVENANCE_SCOPE_NOTICE,
        "claims": normalized,
    }


def build_claim_ui_bundle(
    *,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    graph_path: str | Path = DEFAULT_GRAPH_PATH,
    provenance_path: str | Path | None = DEFAULT_PROVENANCE_PATH,
) -> dict[str, Any]:
    """Fuse ledger, graph, and optional explicit lineage into a read-only UI bundle."""

    ledger = inspect_ledger(ledger_path)
    claims = [deepcopy(claim) for claim in ledger.claims]
    claims_by_id = {str(claim["id"]): claim for claim in claims}

    graph = load_claim_graph(graph_path)
    graph_analysis = analyze_claim_graph(ledger_path, graph_path)
    classification_by_id = {
        finding.claim_id: finding.classification
        for finding in graph_analysis.findings
    }

    provenance_payload: dict[str, Any] | None = None
    provenance_by_id: dict[str, dict[str, Any]] = {}
    if provenance_path is not None:
        provenance_payload = load_claim_provenance(provenance_path)
        for entry in provenance_payload["claims"]:
            claim_id = str(entry["claim_id"])
            if claim_id not in claims_by_id:
                raise ValueError(
                    f"Claim provenance references unknown ledger claim: {claim_id}"
                )
            provenance_by_id[claim_id] = entry

    roots = tuple(str(root) for root in graph["roots"])
    root_set = set(roots)
    edges = [
        {
            "from": str(edge["from"]),
            "to": str(edge["to"]),
            "rationale": str(edge["rationale"]).strip(),
        }
        for edge in graph["edges"]
    ]

    bundle_claims: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = str(claim["id"])
        ledger_provenance = claim.get("provenance")
        if not isinstance(ledger_provenance, dict):
            raise ValueError(f"Ledger claim {claim_id} must contain provenance metadata.")

        recorded_at = ledger_provenance.get("recorded_at")
        record_ref = ledger_provenance.get("record_ref")
        if not isinstance(recorded_at, str) or not recorded_at:
            raise ValueError(f"Ledger claim {claim_id} provenance.recorded_at is required.")
        if not isinstance(record_ref, str) or not record_ref:
            raise ValueError(f"Ledger claim {claim_id} provenance.record_ref is required.")

        explicit = provenance_by_id.get(claim_id, {})
        source_files = _merge_source_files(claim, explicit)
        data_sources = deepcopy(explicit.get("data_sources", []))

        context_snapshot = ledger_provenance.get("context_snapshot")
        if not isinstance(context_snapshot, dict):
            raise ValueError(
                f"Ledger claim {claim_id} provenance.context_snapshot must be an object."
            )

        judgment = claim.get("judgment")
        if not isinstance(judgment, dict):
            raise ValueError(f"Ledger claim {claim_id} judgment must be an object.")

        bundle_claims.append(
            {
                "id": claim_id,
                "status": str(claim["status"]),
                "classification": classification_by_id[claim_id],
                "is_root": claim_id in root_set,
                "claim": str(claim["claim"]),
                "scope": str(claim["scope"]),
                "decision_impact": str(claim["decision_impact"]),
                "logged_at": recorded_at,
                "generated_at": ledger_provenance.get("generated_at"),
                "record_ref": record_ref,
                "context_snapshot": deepcopy(context_snapshot),
                "source_files": source_files,
                "data_sources": data_sources,
                "judgment": deepcopy(judgment),
            }
        )

    return {
        "schema_version": UI_BUNDLE_SCHEMA_VERSION,
        "type": UI_BUNDLE_TYPE,
        "scientific_validation": False,
        "automatic_adjudication": False,
        "read_only": True,
        "scope_notice": UI_SCOPE_NOTICE,
        "generated_from": {
            "ledger": str(ledger_path),
            "graph": str(graph_path),
            "provenance": str(provenance_path) if provenance_path is not None else None,
        },
        "graph": {
            "scope_notice": str(graph.get("scope_notice", GRAPH_SCOPE_NOTICE)),
            "roots": list(roots),
            "edges": edges,
        },
        "claims": bundle_claims,
    }


def write_claim_ui_bundle(
    output_path: str | Path = DEFAULT_UI_BUNDLE_PATH,
    *,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    graph_path: str | Path = DEFAULT_GRAPH_PATH,
    provenance_path: str | Path | None = DEFAULT_PROVENANCE_PATH,
) -> dict[str, Any]:
    bundle = build_claim_ui_bundle(
        ledger_path=ledger_path,
        graph_path=graph_path,
        provenance_path=provenance_path,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return bundle


def _normalize_source_files(value: Any, claim_id: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"Claim provenance {claim_id} source_files must be a list.")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(
                f"Claim provenance {claim_id} source_files[{index}] must be an object."
            )
        if set(item) - {"ref", "role", "note"}:
            raise ValueError(
                f"Claim provenance {claim_id} source_files[{index}] has unsupported fields."
            )
        ref = item.get("ref")
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError(
                f"Claim provenance {claim_id} source_files[{index}].ref is required."
            )
        entry: dict[str, Any] = {"ref": ref.strip()}
        for key in ("role", "note"):
            field = item.get(key)
            if field is not None:
                if not isinstance(field, str) or not field.strip():
                    raise ValueError(
                        f"Claim provenance {claim_id} source_files[{index}].{key} "
                        "must be a non-empty string."
                    )
                entry[key] = field.strip()
        normalized.append(entry)
    return normalized


def _normalize_data_sources(value: Any, claim_id: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"Claim provenance {claim_id} data_sources must be a list.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}] must be an object."
            )
        allowed = {
            "system",
            "catalog",
            "database",
            "schema",
            "table",
            "query",
            "note",
        }
        if set(item) - allowed:
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}] has unsupported fields."
            )

        system = item.get("system")
        table = item.get("table")
        query = item.get("query")
        if not isinstance(system, str) or not system.strip():
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}].system is required."
            )
        if not isinstance(table, str) or not table.strip():
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}].table is required."
            )
        if not isinstance(query, dict):
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}].query is required."
            )

        query_allowed = {"ref", "text", "sha256"}
        if set(query) - query_allowed:
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}].query has unsupported fields."
            )
        query_ref = query.get("ref")
        query_text = query.get("text")
        query_sha = query.get("sha256")
        if not (
            isinstance(query_ref, str) and query_ref.strip()
            or isinstance(query_text, str) and query_text.strip()
        ):
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}].query requires ref or text."
            )
        if query_ref is not None and (
            not isinstance(query_ref, str) or not query_ref.strip()
        ):
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}].query.ref "
                "must be a non-empty string."
            )
        if query_text is not None and (
            not isinstance(query_text, str) or not query_text.strip()
        ):
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}].query.text "
                "must be a non-empty string."
            )
        if query_sha is not None and (
            not isinstance(query_sha, str)
            or len(query_sha) != 64
            or any(char not in "0123456789abcdef" for char in query_sha)
        ):
            raise ValueError(
                f"Claim provenance {claim_id} data_sources[{index}].query.sha256 "
                "must be a lowercase 64-character hex digest."
            )

        entry: dict[str, Any] = {
            "system": system.strip(),
            "table": table.strip(),
            "query": {
                **({"ref": query_ref.strip()} if isinstance(query_ref, str) else {}),
                **({"text": query_text.strip()} if isinstance(query_text, str) else {}),
                **({"sha256": query_sha} if isinstance(query_sha, str) else {}),
            },
        }
        for key in ("catalog", "database", "schema", "note"):
            field = item.get(key)
            if field is not None:
                if not isinstance(field, str) or not field.strip():
                    raise ValueError(
                        f"Claim provenance {claim_id} data_sources[{index}].{key} "
                        "must be a non-empty string."
                    )
                entry[key] = field.strip()
        normalized.append(entry)
    return normalized


def _merge_source_files(
    claim: dict[str, Any],
    explicit: dict[str, Any],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    def add(ref: Any, role: str, note: str | None = None) -> None:
        if not isinstance(ref, str) or not ref.strip():
            return
        clean = ref.strip()
        entry = merged.setdefault(clean, {"ref": clean, "roles": [], "note": None})
        if role not in entry["roles"]:
            entry["roles"].append(role)
        if note and entry["note"] is None:
            entry["note"] = note

    provenance = claim.get("provenance")
    if isinstance(provenance, dict):
        for ref in provenance.get("origin_refs", []):
            add(ref, "origin_ref")
        snapshot = provenance.get("context_snapshot")
        if isinstance(snapshot, dict):
            for ref in snapshot.get("refs", []):
                add(ref, "creation_context")

    evidence = claim.get("evidence")
    if isinstance(evidence, dict):
        for ref in evidence.get("current_refs", []):
            add(ref, "current_evidence")

    judgment = claim.get("judgment")
    if isinstance(judgment, dict):
        for ref in judgment.get("evidence_refs", []):
            add(ref, "judgment_evidence")

    for item in explicit.get("source_files", []):
        role = str(item.get("role") or "declared_source")
        note = item.get("note")
        add(item.get("ref"), role, str(note) if note is not None else None)

    return list(merged.values())
