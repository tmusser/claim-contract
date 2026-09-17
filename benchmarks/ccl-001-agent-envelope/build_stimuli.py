from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from claim_contract.binding import build_profile_manifest_binding
from claim_contract.metadata import TOOL_NAME, TOOL_VERSION
from claim_contract.profiles import get_profile_manifest
from claim_contract.validator import validate_contract


STIMULI_TYPE = "claim_contract.ccl_001_agent_envelope_stimuli"
STIMULI_SCHEMA_VERSION = "1.0"
SCOPE_NOTICE = (
    "These paired stimuli isolate the supplied context difference between bare verdict + "
    "claim text and the full claim-contract report. They contain no agent outputs or "
    "adjudication of CCL-001."
)


def _load_mapping(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping/object at root of {path}.")
    return payload


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def _set_path(target: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    cursor: Any = target
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            raise ValueError(f"Cannot set {dotted_path!r}: parent path is missing.")
        cursor = cursor[part]
    if not isinstance(cursor, dict):
        raise ValueError(f"Cannot set {dotted_path!r}: parent is not a mapping.")
    cursor[parts[-1]] = copy.deepcopy(value)


def _delete_path(target: dict[str, Any], dotted_path: str) -> None:
    parts = dotted_path.split(".")
    cursor: Any = target
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            raise ValueError(f"Cannot delete {dotted_path!r}: parent path is missing.")
        cursor = cursor[part]
    if not isinstance(cursor, dict) or parts[-1] not in cursor:
        raise ValueError(f"Cannot delete {dotted_path!r}: field is missing.")
    del cursor[parts[-1]]


def _materialize_case(corpus: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    bases = corpus.get("base_contracts")
    if not isinstance(bases, dict):
        raise ValueError("source corpus base_contracts must be a mapping.")
    base_name = case.get("base")
    if not isinstance(base_name, str) or base_name not in bases:
        raise ValueError(f"Unknown base contract for case {case.get('id')!r}: {base_name!r}")
    base = bases[base_name]
    if not isinstance(base, dict):
        raise ValueError(f"Base contract {base_name!r} must be a mapping.")

    contract = copy.deepcopy(base)
    mutations = case.get("set", {}) or {}
    deletions = case.get("delete", []) or []
    if not isinstance(mutations, dict):
        raise ValueError(f"Case {case.get('id')!r} set mutations must be a mapping.")
    if not isinstance(deletions, list) or not all(isinstance(item, str) for item in deletions):
        raise ValueError(f"Case {case.get('id')!r} delete mutations must be string paths.")
    overlap = set(mutations).intersection(deletions)
    if overlap:
        raise ValueError(f"Case {case.get('id')!r} both sets and deletes: {sorted(overlap)!r}")

    for dotted_path, value in mutations.items():
        if not isinstance(dotted_path, str) or not dotted_path:
            raise ValueError(f"Case {case.get('id')!r} has an invalid set path.")
        _set_path(contract, dotted_path, value)
    for dotted_path in deletions:
        _delete_path(contract, dotted_path)
    return contract


def _index_records(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    records = payload.get(key)
    if not isinstance(records, list):
        raise ValueError(f"{key} must be a list.")
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"Every {key} record must be a mapping.")
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError(f"Every {key} record must have a non-empty string id.")
        if record_id in indexed:
            raise ValueError(f"Duplicate {key} id: {record_id}")
        indexed[record_id] = record
    return indexed


def build_stimuli(
    benchmark_path: Path,
    cases_path: Path,
    corpus_path: Path,
) -> dict[str, Any]:
    benchmark = _load_mapping(benchmark_path)
    selection_payload = _load_mapping(cases_path)
    corpus = _load_mapping(corpus_path)

    if benchmark.get("target_claim_id") != "CCL-001":
        raise ValueError("Benchmark target_claim_id must be CCL-001.")
    if benchmark.get("profile") != "minimum-v0.1":
        raise ValueError("Benchmark profile must be minimum-v0.1.")
    instruction = benchmark.get("summary_instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError("Benchmark summary_instruction must be non-empty.")

    source = benchmark.get("source_corpus")
    if not isinstance(source, dict):
        raise ValueError("benchmark.source_corpus must be a mapping.")
    expected_blob_sha = source.get("git_blob_sha")
    if not isinstance(expected_blob_sha, str) or len(expected_blob_sha) != 40:
        raise ValueError("benchmark.source_corpus.git_blob_sha must be a 40-character Git blob SHA.")
    actual_blob_sha = _git_blob_sha(corpus_path)
    if actual_blob_sha != expected_blob_sha:
        raise ValueError(
            "Source corpus drifted from the frozen Git blob: "
            f"expected {expected_blob_sha}, got {actual_blob_sha}."
        )

    source_cases = _index_records(corpus, "cases")
    selected_cases = selection_payload.get("cases")
    if not isinstance(selected_cases, list):
        raise ValueError("cases.yaml cases must be a list.")
    expected_count = benchmark.get("case_count")
    if not isinstance(expected_count, int) or expected_count < 1:
        raise ValueError("benchmark.case_count must be a positive integer.")
    if len(selected_cases) != expected_count:
        raise ValueError(
            f"Expected {expected_count} selected cases; found {len(selected_cases)}."
        )

    seen: set[str] = set()
    stimuli: list[dict[str, Any]] = []
    for selected in selected_cases:
        if not isinstance(selected, dict):
            raise ValueError("Every selected case must be a mapping.")
        case_id = selected.get("id")
        family = selected.get("family")
        if not isinstance(case_id, str) or case_id not in source_cases:
            raise ValueError(f"Unknown selected source case: {case_id!r}")
        if case_id in seen:
            raise ValueError(f"Duplicate selected case: {case_id}")
        seen.add(case_id)
        if not isinstance(family, str) or not family:
            raise ValueError(f"Selected case {case_id} must declare a family.")

        source_case = source_cases[case_id]
        contract = _materialize_case(corpus, source_case)
        report = validate_contract(contract).to_dict()
        verdict = report.get("verdict")
        claim_text = report.get("claim_text")
        if verdict not in {"READY", "REVIEW", "BLOCK"}:
            raise ValueError(f"Generated case {case_id} has unsupported verdict {verdict!r}.")
        if not isinstance(claim_text, str) or not claim_text:
            raise ValueError(f"Generated case {case_id} has no claim text.")

        stimuli.append(
            {
                "case_id": case_id,
                "family": family,
                "source_description": source_case.get("description", ""),
                "instruction": instruction,
                "reference_verdict": verdict,
                "claim_text": claim_text,
                "arms": {
                    "bare_verdict_claim": {
                        "verdict": verdict,
                        "claim_text": claim_text,
                    },
                    "full_envelope": report,
                },
            }
        )

    manifest = get_profile_manifest("minimum-v0.1")
    manifest_binding = build_profile_manifest_binding(manifest.to_dict())
    return {
        "schema_version": STIMULI_SCHEMA_VERSION,
        "type": STIMULI_TYPE,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "scientific_validation": False,
        "automatic_adjudication": False,
        "scope_notice": SCOPE_NOTICE,
        "benchmark_version": str(benchmark.get("benchmark_version", "")),
        "target_claim_id": "CCL-001",
        "profile": "minimum-v0.1",
        "source_corpus": {
            "path": str(source.get("path", "")),
            "git_blob_sha": actual_blob_sha,
            "repository_revision": str(source.get("repository_revision", "")),
        },
        "profile_manifest_binding": manifest_binding.to_dict(),
        "case_count": len(stimuli),
        "arms": ["bare_verdict_claim", "full_envelope"],
        "stimuli": stimuli,
    }


def build_parser() -> argparse.ArgumentParser:
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    parser = argparse.ArgumentParser(
        description="Build frozen paired CCL-001 stimuli without running any agent model."
    )
    parser.add_argument("--benchmark", type=Path, default=here / "benchmark.yaml")
    parser.add_argument("--cases", type=Path, default=here / "cases.yaml")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=root / "benchmarks" / "minimum-v0.1" / "corpus.yaml",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        artifact = build_stimuli(args.benchmark, args.cases, args.corpus)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
