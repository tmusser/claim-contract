from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).parents[1]
BENCHMARK_DIR = ROOT / "benchmarks/minimum-v0.1"
CORPUS_PATH = BENCHMARK_DIR / "corpus.yaml"
LABELS_PATH = BENCHMARK_DIR / "labels.yaml"
MANIFEST_PATH = BENCHMARK_DIR / "benchmark.yaml"
RESULT_SCHEMA_PATH = ROOT / "schemas/benchmark-result-v1.schema.json"
EVALUATOR_PATH = BENCHMARK_DIR / "evaluate.py"


def _load_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_evaluator():
    spec = importlib.util.spec_from_file_location("minimum_v0_1_evaluator", EVALUATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_benchmark_has_required_size_balance_and_families() -> None:
    manifest = _load_yaml(MANIFEST_PATH)
    corpus = _load_yaml(CORPUS_PATH)
    labels_payload = _load_yaml(LABELS_PATH)

    cases = corpus["cases"]
    labels = labels_payload["labels"]
    assert manifest["case_count"] == 50
    assert len(cases) == 50
    assert len(labels) == 50

    case_ids = [case["id"] for case in cases]
    label_ids = [label["id"] for label in labels]
    assert len(set(case_ids)) == 50
    assert len(set(label_ids)) == 50
    assert set(case_ids) == set(label_ids)

    blocking = sum(label["blocking_violation"] is True for label in labels)
    nonblocking = sum(label["blocking_violation"] is False for label in labels)
    assert blocking == 25
    assert nonblocking == 25
    assert manifest["label_counts"] == {
        "blocking_violation": 25,
        "nonblocking_or_review": 25,
    }

    families = {label["family"] for label in labels}
    required = {
        "descriptive",
        "provenance",
        "comparison_groups",
        "relative_baseline",
        "uncertainty",
        "multiplicity",
        "magnitude",
        "causal_design",
        "randomization_integrity",
        "identifying_assumptions",
    }
    assert required <= families


def test_labels_do_not_encode_validator_answers() -> None:
    labels_payload = _load_yaml(LABELS_PATH)
    serialized = json.dumps(labels_payload, sort_keys=True)

    assert re.search(r"\bCC[0-9]{3}\b", serialized) is None
    assert '"expected_verdict"' not in serialized
    assert '"expected_rule_id"' not in serialized
    assert '"expected_rule_ids"' not in serialized

    for label in labels_payload["labels"]:
        assert set(label) == {"id", "blocking_violation", "family", "rationale"}
        assert isinstance(label["blocking_violation"], bool)


def test_all_frozen_cases_materialize_without_scoring_them() -> None:
    evaluator = _load_evaluator()
    corpus = _load_yaml(CORPUS_PATH)

    for case in corpus["cases"]:
        contract = evaluator.materialize_case(corpus, case)
        assert isinstance(contract, dict)
        assert contract.get("profile") == "minimum-v0.1"


def test_freeze_manifest_defers_first_score() -> None:
    manifest = _load_yaml(MANIFEST_PATH)
    freeze = manifest["freeze_policy"]

    assert manifest["labeling_status"] == "frozen-before-first-scoring"
    assert manifest["results_status"] == "unobserved-in-freeze-commit"
    assert freeze["labels_are_independent_of_validator_rule_ids"] is True
    assert freeze["expected_validator_verdicts_are_not_recorded"] is True
    assert freeze["expected_validator_rule_ids_are_not_recorded"] is True
    assert freeze["frozen_corpus_is_not_scored_by_repository_ci"] is True
    assert freeze["first_score_should_reference_a_merged_freeze_revision"] is True
    assert freeze["evaluator_does_not_adjudicate_target_claim"] is True


def test_evaluator_mechanics_on_separate_tiny_fixture(tmp_path: Path) -> None:
    evaluator = _load_evaluator()

    ready = {
        "version": "0.1",
        "profile": "minimum-v0.1",
        "claim": {
            "text": "Activation was 27% among eligible users.",
            "type": "descriptive",
            "population": "eligible users",
            "time_window": "2026-Q2",
            "metric": {
                "name": "activation_rate",
                "unit": "proportion",
                "definition": "activated / eligible",
            },
        },
        "evidence": {
            "design": "descriptive_summary",
            "sample_size": 1000,
            "estimate": {"value": 0.27, "scale": "absolute"},
            "uncertainty": {"method": "interval", "lower": 0.24, "upper": 0.30},
            "provenance": {"source": "tiny.fixture"},
            "checks": {
                "metric_definition_locked": True,
                "missingness_assessed": True,
                "composition_stability_assessed": True,
                "treatment_assignment_validated": False,
                "identifying_assumptions_documented": False,
            },
            "caveats": [],
        },
    }
    corpus = {
        "schema_version": "1.0",
        "type": "test.corpus",
        "profile": "minimum-v0.1",
        "base_contracts": {"ready": ready},
        "cases": [
            {"id": "D001", "base": "ready"},
            {"id": "D002", "base": "ready", "delete": ["claim.population"]},
        ],
    }
    labels = {
        "schema_version": "1.0",
        "type": "test.labels",
        "benchmark_version": "1.0",
        "target_claim_id": "CCL-002",
        "labels": [
            {
                "id": "D001",
                "blocking_violation": False,
                "family": "descriptive",
                "rationale": "complete",
            },
            {
                "id": "D002",
                "blocking_violation": True,
                "family": "scope",
                "rationale": "population absent",
            },
        ],
    }
    corpus_path = tmp_path / "corpus.yaml"
    labels_path = tmp_path / "labels.yaml"
    corpus_path.write_text(yaml.safe_dump(corpus, sort_keys=False), encoding="utf-8")
    labels_path.write_text(yaml.safe_dump(labels, sort_keys=False), encoding="utf-8")

    result = evaluator.evaluate(corpus_path, labels_path)
    assert result["automatic_adjudication"] is False
    assert result["scientific_validation"] is False
    assert result["metrics"]["block_recall"] == 1.0
    assert result["metrics"]["false_block_rate"] == 0.0
    assert result["metrics"]["all_block_rule_ids_documented"] is True

    schema = json.loads(RESULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(result, schema)
