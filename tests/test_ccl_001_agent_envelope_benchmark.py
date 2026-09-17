from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import jsonschema
import pytest
import yaml


ROOT = Path(__file__).parents[1]
BENCH = ROOT / "benchmarks" / "ccl-001-agent-envelope"
MINIMUM_CORPUS = ROOT / "benchmarks" / "minimum-v0.1" / "corpus.yaml"
STIMULI_SCHEMA = ROOT / "schemas" / "ccl-001-agent-envelope-stimuli-v1.schema.json"
RESULT_SCHEMA = ROOT / "schemas" / "ccl-001-agent-envelope-result-v1.schema.json"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_module(BENCH / "build_stimuli.py", "ccl001_builder")
evaluator = _load_module(BENCH / "evaluate.py", "ccl001_evaluator")


def _yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build() -> dict:
    return builder.build_stimuli(
        BENCH / "benchmark.yaml",
        BENCH / "cases.yaml",
        MINIMUM_CORPUS,
    )


def test_frozen_selection_is_30_cases_balanced_across_analytical_families() -> None:
    benchmark = _yaml(BENCH / "benchmark.yaml")
    cases = _yaml(BENCH / "cases.yaml")["cases"]

    assert benchmark["target_claim_id"] == "CCL-001"
    assert benchmark["case_count"] == 30
    assert len(cases) == 30
    assert len({case["id"] for case in cases}) == 30
    assert Counter(case["family"] for case in cases) == {
        "descriptive": 6,
        "comparison": 6,
        "observational": 6,
        "randomized": 6,
        "quasi_experimental": 6,
    }


def test_freeze_metadata_explicitly_precedes_model_outputs_and_annotations() -> None:
    benchmark = _yaml(BENCH / "benchmark.yaml")
    freeze = benchmark["freeze_policy"]

    assert freeze["case_selection_frozen_before_model_runs"] is True
    assert freeze["instruction_frozen_before_model_runs"] is True
    assert freeze["annotation_rubric_frozen_before_model_runs"] is True
    assert freeze["model_outputs_observed_in_freeze_commit"] is False
    assert freeze["annotations_observed_in_freeze_commit"] is False
    assert freeze["results_observed_in_freeze_commit"] is False
    assert freeze["evaluator_does_not_adjudicate_target_claim"] is True
    assert not (BENCH / "results").exists()


def test_stimulus_builder_is_pinned_and_preserves_only_the_treatment_difference() -> None:
    artifact = _build()
    schema = _json(STIMULI_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(artifact, schema)

    assert artifact["case_count"] == 30
    assert artifact["source_corpus"]["git_blob_sha"] == "1579cba5ad6aa99032be67f347f28aa74d63e59e"
    assert artifact["scientific_validation"] is False
    assert artifact["automatic_adjudication"] is False

    verdicts = set()
    instructions = set()
    for stimulus in artifact["stimuli"]:
        verdicts.add(stimulus["reference_verdict"])
        instructions.add(stimulus["instruction"])
        bare = stimulus["arms"]["bare_verdict_claim"]
        full = stimulus["arms"]["full_envelope"]

        assert bare == {
            "verdict": stimulus["reference_verdict"],
            "claim_text": stimulus["claim_text"],
        }
        assert full["verdict"] == stimulus["reference_verdict"]
        assert full["claim_text"] == stimulus["claim_text"]
        assert full["type"] == "claim_contract.report"
        assert full["scientific_validation"] is False

    assert verdicts == {"READY", "REVIEW", "BLOCK"}
    assert len(instructions) == 1


def test_builder_fails_closed_if_source_corpus_bytes_drift(tmp_path: Path) -> None:
    changed = tmp_path / "corpus.yaml"
    changed.write_bytes(MINIMUM_CORPUS.read_bytes() + b"\n# drift\n")

    with pytest.raises(ValueError, match="Source corpus drifted"):
        builder.build_stimuli(
            BENCH / "benchmark.yaml",
            BENCH / "cases.yaml",
            changed,
        )


def _write_synthetic_evidence(tmp_path: Path) -> tuple[Path, Path, Path]:
    stimuli = _build()
    stimuli_path = tmp_path / "stimuli.json"
    stimuli_path.write_text(json.dumps(stimuli, indent=2) + "\n", encoding="utf-8")
    stimuli_sha = _sha256_file(stimuli_path)
    case_ids = [record["case_id"] for record in stimuli["stimuli"]]

    model_families = []
    annotations = []
    for family_index, family in enumerate(("family-a", "family-b")):
        responses = []
        for case_index, case_id in enumerate(case_ids):
            for arm in ("bare_verdict_claim", "full_envelope"):
                text = f"{family} {case_id} {arm} synthetic output"
                responses.append({"case_id": case_id, "arm": arm, "text": text})
                if arm == "bare_verdict_claim":
                    unsafe = case_index < 9
                    verdict_reporting = "correct"
                else:
                    unsafe = case_index < 2
                    verdict_reporting = "omitted" if case_index == family_index else "correct"
                annotations.append(
                    {
                        "model_family": family,
                        "case_id": case_id,
                        "arm": arm,
                        "response_sha256": _sha256_text(text),
                        "unsafe_overstatement": unsafe,
                        "unsafe_tags": ["scientific_validation_upgrade"] if unsafe else [],
                        "verdict_reporting": verdict_reporting,
                        "annotator": "synthetic-test-annotator",
                        "note": None,
                    }
                )
        model_families.append(
            {
                "family": family,
                "model_id": f"{family}-model-v1",
                "decoding_settings": {"temperature": 0},
                "responses": responses,
            }
        )

    runs_path = tmp_path / "runs.yaml"
    runs_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "type": "claim_contract.ccl_001_agent_envelope_runs",
                "stimuli_sha256": stimuli_sha,
                "model_families": model_families,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    annotations_path = tmp_path / "annotations.yaml"
    annotations_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "type": "claim_contract.ccl_001_agent_envelope_annotations",
                "stimuli_sha256": stimuli_sha,
                "annotations": annotations,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return stimuli_path, runs_path, annotations_path


def test_evaluator_computes_judge_relevant_metrics_without_adjudicating(tmp_path: Path) -> None:
    stimuli_path, runs_path, annotations_path = _write_synthetic_evidence(tmp_path)
    result = evaluator.evaluate(stimuli_path, runs_path, annotations_path)

    schema = _json(RESULT_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(result, schema)

    assert result["automatic_adjudication"] is False
    assert "judgment" not in result
    assert result["benchmark"]["case_count"] == 30
    assert result["benchmark"]["model_family_count"] == 2

    pooled = result["metrics"]["pooled"]
    assert pooled["bare_verdict_claim"]["n"] == 60
    assert pooled["full_envelope"]["n"] == 60
    assert pooled["bare_verdict_claim"]["unsafe_count"] == 18
    assert pooled["full_envelope"]["unsafe_count"] == 4
    assert pooled["unsafe_rate_reduction_pp"] == pytest.approx(23.3333333333)
    assert pooled["correct_verdict_rate_drop_pp"] == pytest.approx(3.3333333333)
    assert result["metrics"]["full_unsafe_not_worse_in_every_family"] is True


def test_evaluator_rejects_annotation_detached_from_raw_output(tmp_path: Path) -> None:
    stimuli_path, runs_path, annotations_path = _write_synthetic_evidence(tmp_path)
    payload = _yaml(annotations_path)
    payload["annotations"][0]["response_sha256"] = "0" * 64
    annotations_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="response_sha256 does not match"):
        evaluator.evaluate(stimuli_path, runs_path, annotations_path)


def test_evaluator_requires_two_complete_model_families(tmp_path: Path) -> None:
    stimuli_path, runs_path, annotations_path = _write_synthetic_evidence(tmp_path)
    runs = _yaml(runs_path)
    runs["model_families"] = runs["model_families"][:1]
    runs_path.write_text(yaml.safe_dump(runs, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="at least two model families"):
        evaluator.evaluate(stimuli_path, runs_path, annotations_path)
