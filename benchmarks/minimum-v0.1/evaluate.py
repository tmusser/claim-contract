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
from claim_contract.models import Severity, Verdict
from claim_contract.profiles import get_profile_manifest
from claim_contract.validator import validate_contract


BENCHMARK_TYPE = "claim_contract.minimum_v0_1_benchmark_result"
BENCHMARK_SCHEMA_VERSION = "1.0"
SCOPE_NOTICE = (
    "This artifact measures minimum-v0.1 BLOCK behavior against frozen benchmark labels. "
    "It is not scientific validation and does not automatically adjudicate CCL-002."
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


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def materialize_case(corpus: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    bases = corpus.get("base_contracts")
    if not isinstance(bases, dict):
        raise ValueError("corpus.base_contracts must be a mapping.")
    base_name = case.get("base")
    if not isinstance(base_name, str) or base_name not in bases:
        raise ValueError(f"Unknown base contract for case {case.get('id')!r}: {base_name!r}")
    base = bases[base_name]
    if not isinstance(base, dict):
        raise ValueError(f"Base contract {base_name!r} must be a mapping.")

    contract = copy.deepcopy(base)
    mutations = case.get("set", {})
    deletions = case.get("delete", [])
    if mutations is None:
        mutations = {}
    if deletions is None:
        deletions = []
    if not isinstance(mutations, dict):
        raise ValueError(f"Case {case.get('id')!r} set mutations must be a mapping.")
    if not isinstance(deletions, list) or not all(isinstance(item, str) for item in deletions):
        raise ValueError(f"Case {case.get('id')!r} delete mutations must be string paths.")
    overlap = set(mutations).intersection(deletions)
    if overlap:
        raise ValueError(
            f"Case {case.get('id')!r} both sets and deletes: {sorted(overlap)!r}"
        )

    for dotted_path, value in mutations.items():
        if not isinstance(dotted_path, str) or not dotted_path:
            raise ValueError(f"Case {case.get('id')!r} has an invalid set path.")
        _set_path(contract, dotted_path, value)
    for dotted_path in deletions:
        _delete_path(contract, dotted_path)
    return contract


def _indexed_records(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
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


def evaluate(corpus_path: Path, labels_path: Path) -> dict[str, Any]:
    corpus = _load_mapping(corpus_path)
    labels_payload = _load_mapping(labels_path)

    cases = _indexed_records(corpus, "cases")
    labels = _indexed_records(labels_payload, "labels")
    if set(cases) != set(labels):
        missing_labels = sorted(set(cases) - set(labels))
        extra_labels = sorted(set(labels) - set(cases))
        raise ValueError(
            f"Case/label IDs differ; missing_labels={missing_labels}, extra_labels={extra_labels}"
        )

    profile = corpus.get("profile")
    if profile != "minimum-v0.1":
        raise ValueError(f"Expected corpus profile 'minimum-v0.1'; got {profile!r}.")
    manifest = get_profile_manifest(profile)
    documented_rule_ids = {rule.rule_id for rule in manifest.rules}
    manifest_binding = build_profile_manifest_binding(manifest.to_dict())

    case_results: list[dict[str, Any]] = []
    blocking_count = 0
    nonblocking_count = 0
    true_blocks = 0
    false_blocks = 0
    untraceable_block_ids: set[str] = set()

    for case_id in sorted(cases):
        label = labels[case_id]
        blocking_label = label.get("blocking_violation")
        if not isinstance(blocking_label, bool):
            raise ValueError(f"Label {case_id} blocking_violation must be boolean.")
        family = label.get("family")
        if not isinstance(family, str) or not family:
            raise ValueError(f"Label {case_id} family must be a non-empty string.")

        contract = materialize_case(corpus, cases[case_id])
        report = validate_contract(contract)
        is_block = report.verdict is Verdict.BLOCK
        block_rule_ids = sorted(
            {finding.rule_id for finding in report.findings if finding.severity is Severity.BLOCK}
        )
        untraceable = sorted(set(block_rule_ids) - documented_rule_ids)
        untraceable_block_ids.update(untraceable)

        if blocking_label:
            blocking_count += 1
            true_blocks += int(is_block)
        else:
            nonblocking_count += 1
            false_blocks += int(is_block)

        case_results.append(
            {
                "id": case_id,
                "family": family,
                "label_blocking_violation": blocking_label,
                "validator_verdict": report.verdict.value,
                "block_rule_ids": block_rule_ids,
                "untraceable_block_rule_ids": untraceable,
            }
        )

    if blocking_count == 0 or nonblocking_count == 0:
        raise ValueError("Benchmark requires both blocking and nonblocking labels.")

    block_recall = true_blocks / blocking_count
    false_block_rate = false_blocks / nonblocking_count

    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "type": BENCHMARK_TYPE,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "scientific_validation": False,
        "automatic_adjudication": False,
        "scope_notice": SCOPE_NOTICE,
        "benchmark": {
            "version": str(labels_payload.get("benchmark_version", "")),
            "target_claim_id": str(labels_payload.get("target_claim_id", "")),
            "profile": profile,
            "case_count": len(case_results),
            "corpus_sha256": _sha256_file(corpus_path),
            "labels_sha256": _sha256_file(labels_path),
            "profile_manifest_binding": manifest_binding.to_dict(),
        },
        "metrics": {
            "label_defined_blocking_cases": blocking_count,
            "label_defined_nonblocking_cases": nonblocking_count,
            "validator_blocks_on_blocking_cases": true_blocks,
            "missed_blocking_cases": blocking_count - true_blocks,
            "validator_blocks_on_nonblocking_cases": false_blocks,
            "block_recall": block_recall,
            "false_block_rate": false_block_rate,
            "all_block_rule_ids_documented": not untraceable_block_ids,
            "untraceable_block_rule_ids": sorted(untraceable_block_ids),
        },
        "cases": case_results,
    }


def build_parser() -> argparse.ArgumentParser:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Score minimum-v0.1 against a frozen benchmark without adjudicating CCL-002."
    )
    parser.add_argument("--corpus", type=Path, default=here / "corpus.yaml")
    parser.add_argument("--labels", type=Path, default=here / "labels.yaml")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate(args.corpus, args.labels)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
