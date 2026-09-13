from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

from claim_contract.claim_dag import (
    analyze_claim_dag,
    load_claim_dag,
    render_claim_dag_mermaid,
    validate_claim_dag,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "claim-dag-v1.schema.json"
DAG_PATH = ROOT / "examples" / "claim_dag" / "dag.yaml"


def _load_schema() -> dict[str, object]:
    value = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _load_raw_dag() -> dict[str, object]:
    value = yaml.safe_load(DAG_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_claim_dag_schema_and_example_are_valid() -> None:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_load_raw_dag())
    validate_claim_dag(_load_raw_dag())


def test_runtime_loader_accepts_example() -> None:
    dag = load_claim_dag(DAG_PATH)
    assert dag["type"] == "claim_contract.claim_dag"
    assert dag["scientific_validation"] is False
    assert dag["automatic_adjudication"] is False
    assert dag["mutates_source_artifacts"] is False


def test_analysis_propagates_only_required_path_attention() -> None:
    analysis = analyze_claim_dag(_load_raw_dag())

    assert analysis["exposed_root_claim_ids"] == [
        "claim_reuse_result_in_board_deck",
        "claim_ship_redesign",
    ]
    assert analysis["root_required_depth"] == {
        "claim_ship_redesign": 3,
        "claim_reuse_result_in_board_deck": 3,
    }

    signal_pairs = {
        (signal["root_claim_id"], signal["dependency_id"], signal["attention"])
        for signal in analysis["signals"]
    }
    for root_id in (
        "claim_ship_redesign",
        "claim_reuse_result_in_board_deck",
    ):
        assert (
            root_id,
            "assumption_population_comparable",
            "WATCH",
        ) in signal_pairs
        assert (root_id, "claim_effect_material", "WATCH") in signal_pairs
        assert (root_id, "evidence_uncertainty", "MISSING") in signal_pairs

    assert analysis["shared_fragile_dependency_ids"] == [
        "assumption_population_comparable",
        "claim_effect_material",
        "evidence_uncertainty",
    ]


def test_supported_by_attention_does_not_propagate_as_required_exposure() -> None:
    dag = deepcopy(_load_raw_dag())
    evidence = next(
        node
        for node in dag["nodes"]
        if node["id"] == "evidence_before_after_estimate"
    )
    evidence["attention"] = {
        "state": "CHALLENGED",
        "reason": "Synthetic test-only challenge.",
        "refs": ["tests/test_claim_dag.py"],
    }

    analysis = analyze_claim_dag(dag)
    assert all(
        signal["dependency_id"] != "evidence_before_after_estimate"
        for signal in analysis["signals"]
    )


def test_none_attention_rejects_non_null_reason() -> None:
    dag = deepcopy(_load_raw_dag())
    dag["nodes"][0]["attention"]["reason"] = "Looks fine."

    with pytest.raises(ValueError, match="must be null when state is NONE"):
        validate_claim_dag(dag)

    with pytest.raises(ValidationError):
        Draft202012Validator(_load_schema()).validate(dag)


def test_unknown_edge_target_is_rejected() -> None:
    dag = deepcopy(_load_raw_dag())
    dag["edges"][0]["to"] = "not_a_node"

    with pytest.raises(ValueError, match="unknown target node"):
        validate_claim_dag(dag)


def test_non_claim_edge_source_is_rejected() -> None:
    dag = deepcopy(_load_raw_dag())
    dag["edges"].append(
        {
            "from": "assumption_population_comparable",
            "to": "evidence_uncertainty",
            "relation": "REQUIRES",
            "note": "Invalid test edge.",
        }
    )

    with pytest.raises(ValueError, match="must have kind CLAIM"):
        validate_claim_dag(dag)


def test_cycles_are_rejected() -> None:
    dag = deepcopy(_load_raw_dag())
    dag["edges"].append(
        {
            "from": "claim_effect_material",
            "to": "claim_ship_redesign",
            "relation": "REQUIRES",
            "note": "Synthetic cycle for rejection test.",
        }
    )

    with pytest.raises(ValueError, match="contains a cycle"):
        validate_claim_dag(dag)


def test_mermaid_render_preserves_relationship_and_attention_semantics() -> None:
    rendered = render_claim_dag_mermaid(_load_raw_dag())

    assert rendered.startswith("flowchart TD")
    assert "Structural fragility triage only; not scientific validation" in rendered
    assert "-->|requires|" in rendered
    assert "-.->|supported by|" in rendered
    assert "classDef watch" in rendered
    assert "classDef missing" in rendered
    assert "classDef exposed" in rendered
