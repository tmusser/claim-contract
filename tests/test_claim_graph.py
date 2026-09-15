from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from claim_contract.claim_graph import (
    CONNECTED,
    GRAPH_SCOPE_NOTICE,
    PRUNE_CANDIDATE,
    RETIRED,
    ROOT,
    analyze_claim_graph,
    main,
)


def _write_ledger(path: Path, claims: list[tuple[str, str]]) -> None:
    payload = {
        "schema_version": "1.2",
        "type": "claim_contract.claim_ledger",
        "scope_notice": (
            "Ledger judgments record whether a frozen evidence condition was met. "
            "They are not scientific validation and do not prove a claim universally "
            "true or false."
        ),
        "claims": [{"id": claim_id, "status": status} for claim_id, status in claims],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_graph(
    path: Path,
    *,
    roots: list[str],
    edges: list[dict[str, str]],
) -> None:
    payload = {
        "schema_version": "1.0",
        "type": "claim_contract.claim_graph",
        "scope_notice": GRAPH_SCOPE_NOTICE,
        "roots": roots,
        "edges": edges,
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_live_graph_is_schema_valid_and_current_claims_are_roots() -> None:
    graph = yaml.safe_load(Path("claims/graph.yaml").read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/claim-graph-v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(graph)

    report = analyze_claim_graph("claims/ledger.yaml", "claims/graph.yaml")
    by_id = {finding.claim_id: finding for finding in report.findings}
    assert set(by_id) == {"CCL-001", "CCL-002", "CCL-003"}
    assert all(finding.classification == ROOT for finding in report.findings)
    assert report.prune_candidates == ()


def test_disconnected_active_claim_is_flagged_without_mutation(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    graph = tmp_path / "graph.yaml"
    _write_ledger(
        ledger,
        [("CCL-001", "OPEN"), ("CCL-002", "OPEN"), ("CCL-003", "OPEN")],
    )
    _write_graph(
        graph,
        roots=["CCL-001"],
        edges=[
            {
                "from": "CCL-002",
                "to": "CCL-001",
                "rationale": "Narrow claim contributes to the root claim.",
            }
        ],
    )

    before = ledger.read_text(encoding="utf-8")
    report = analyze_claim_graph(ledger, graph)
    after = ledger.read_text(encoding="utf-8")
    by_id = {finding.claim_id: finding for finding in report.findings}

    assert by_id["CCL-001"].classification == ROOT
    assert by_id["CCL-002"].classification == CONNECTED
    assert by_id["CCL-002"].path_to_root == ("CCL-002", "CCL-001")
    assert by_id["CCL-003"].classification == PRUNE_CANDIDATE
    assert by_id["CCL-003"].structurally_extraneous is True
    assert by_id["CCL-003"].path_to_root is None
    assert before == after

    payload = report.to_dict()
    assert payload["scientific_validation"] is False
    assert payload["automatic_retirement"] is False
    assert payload["mutates_ledger"] is False
    assert payload["counts"]["prune_candidates"] == 1


def test_retired_claim_is_not_a_candidate_or_active_bridge(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    graph = tmp_path / "graph.yaml"
    _write_ledger(
        ledger,
        [
            ("CCL-001", "OPEN"),
            ("CCL-002", "RETIRED"),
            ("CCL-003", "OPEN"),
        ],
    )
    _write_graph(
        graph,
        roots=["CCL-001"],
        edges=[
            {
                "from": "CCL-003",
                "to": "CCL-002",
                "rationale": "Historical relationship only.",
            },
            {
                "from": "CCL-002",
                "to": "CCL-001",
                "rationale": "Historical relationship only.",
            },
        ],
    )

    report = analyze_claim_graph(ledger, graph)
    by_id = {finding.claim_id: finding for finding in report.findings}
    assert by_id["CCL-002"].classification == RETIRED
    assert by_id["CCL-002"].structurally_extraneous is False
    assert by_id["CCL-003"].classification == PRUNE_CANDIDATE


def test_unknown_claim_reference_fails_closed(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    graph = tmp_path / "graph.yaml"
    _write_ledger(ledger, [("CCL-001", "OPEN")])
    _write_graph(
        graph,
        roots=["CCL-001"],
        edges=[
            {
                "from": "CCL-999",
                "to": "CCL-001",
                "rationale": "Invalid reference.",
            }
        ],
    )

    with pytest.raises(ValueError, match="unknown claim ID"):
        analyze_claim_graph(ledger, graph)


def test_relevance_cycle_fails_closed(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    graph = tmp_path / "graph.yaml"
    _write_ledger(
        ledger,
        [("CCL-001", "OPEN"), ("CCL-002", "OPEN"), ("CCL-003", "OPEN")],
    )
    _write_graph(
        graph,
        roots=["CCL-001"],
        edges=[
            {"from": "CCL-002", "to": "CCL-003", "rationale": "A."},
            {"from": "CCL-003", "to": "CCL-002", "rationale": "B."},
        ],
    )

    with pytest.raises(ValueError, match="relevance cycle"):
        analyze_claim_graph(ledger, graph)


def test_retired_root_fails_closed(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    graph = tmp_path / "graph.yaml"
    _write_ledger(ledger, [("CCL-001", "RETIRED")])
    _write_graph(graph, roots=["CCL-001"], edges=[])

    with pytest.raises(ValueError, match="Retired claims cannot be graph roots"):
        analyze_claim_graph(ledger, graph)


def test_cli_can_gate_on_prune_candidates(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger = tmp_path / "ledger.yaml"
    graph = tmp_path / "graph.yaml"
    _write_ledger(ledger, [("CCL-001", "OPEN"), ("CCL-002", "OPEN")])
    _write_graph(graph, roots=["CCL-001"], edges=[])

    code = main(
        [
            "prune",
            str(ledger),
            "--graph",
            str(graph),
            "--json",
            "--fail-on-candidate",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    assert payload["counts"]["prune_candidates"] == 1
    assert payload["claims"][1]["classification"] == PRUNE_CANDIDATE
