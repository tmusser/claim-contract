from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .binding import (
    ContractBinding,
    ProfileManifestBinding,
    build_contract_binding,
    build_profile_manifest_binding,
    contract_binding_from_dict,
)
from .metadata import (
    EVIDENCE_RECEIPT_INSPECTION_SCHEMA_VERSION,
    EVIDENCE_RECEIPT_INSPECTION_TYPE,
    EVIDENCE_RECEIPTS_SCHEMA_VERSION,
    EVIDENCE_RECEIPTS_TYPE,
    TOOL_NAME,
    TOOL_VERSION,
)
from .profiles import DEFAULT_PROFILE, get_profile_manifest
from .trace import build_rule_trace
from .validator import TRACE_NOT_APPLICABLE


RECEIPTS_SCOPE_NOTICE = (
    "Receipt coverage records retained repository references for declared evidence fields. "
    "A receipt does not verify that the referenced material proves, correctly computes, or "
    "adequately supports the declaration and is not scientific validation."
)

RECEIPTED = "RECEIPTED"
UNRECEIPTED = "UNRECEIPTED"


@dataclass(frozen=True)
class EvidenceReceipt:
    field: str
    refs: tuple[str, ...]
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "field": self.field,
            "refs": list(self.refs),
        }
        if self.note is not None:
            payload["note"] = self.note
        return payload


@dataclass(frozen=True)
class ReceiptCoverage:
    field: str
    status: str
    applicable_rule_ids: tuple[str, ...]
    refs: tuple[str, ...] = ()
    refs_resolve: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "status": self.status,
            "applicable_rule_ids": list(self.applicable_rule_ids),
            "refs": list(self.refs),
            "refs_resolve": self.refs_resolve,
        }


@dataclass(frozen=True)
class EvidenceReceiptInspection:
    saved_binding: ContractBinding
    current_binding: ContractBinding
    profile: str
    profile_manifest_binding: ProfileManifestBinding
    repository_revision: str
    revision_resolves: bool
    coverage: tuple[ReceiptCoverage, ...]
    unused_receipts: tuple[EvidenceReceipt, ...]
    missing_refs: tuple[str, ...]
    invalid_refs: tuple[str, ...]

    @property
    def contract_binding_matches(self) -> bool:
        return self.saved_binding == self.current_binding

    @property
    def integrity_ok(self) -> bool:
        return bool(
            self.contract_binding_matches
            and self.revision_resolves
            and not self.missing_refs
            and not self.invalid_refs
        )

    @property
    def receipted_count(self) -> int:
        return sum(item.status == RECEIPTED for item in self.coverage)

    @property
    def unreceipted_count(self) -> int:
        return sum(item.status == UNRECEIPTED for item in self.coverage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EVIDENCE_RECEIPT_INSPECTION_SCHEMA_VERSION,
            "type": EVIDENCE_RECEIPT_INSPECTION_TYPE,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "scientific_validation": False,
            "automatic_verification": False,
            "changes_validation_verdict": False,
            "scope_notice": RECEIPTS_SCOPE_NOTICE,
            "contract": {
                "binding_match": self.contract_binding_matches,
                "saved_input_binding": self.saved_binding.to_dict(),
                "current_input_binding": self.current_binding.to_dict(),
                "profile": self.profile,
                "profile_manifest_binding": self.profile_manifest_binding.to_dict(),
            },
            "snapshot": {
                "repository_revision": self.repository_revision,
                "revision_resolves": self.revision_resolves,
                "missing_refs": list(self.missing_refs),
                "invalid_refs": list(self.invalid_refs),
            },
            "summary": {
                "integrity_ok": self.integrity_ok,
                "applicable_evidence_field_count": len(self.coverage),
                "receipted_count": self.receipted_count,
                "unreceipted_count": self.unreceipted_count,
                "unused_receipt_count": len(self.unused_receipts),
            },
            "coverage": [item.to_dict() for item in self.coverage],
            "unused_receipts": [receipt.to_dict() for receipt in self.unused_receipts],
        }


def load_evidence_receipts(path: str | Path) -> dict[str, Any]:
    receipt_path = Path(path)
    if not receipt_path.exists():
        raise FileNotFoundError(f"Evidence receipts file not found: {receipt_path}")

    text = receipt_path.read_text(encoding="utf-8")
    suffix = receipt_path.suffix.lower()
    try:
        if suffix == ".json":
            value = json.loads(text)
        elif suffix in {".yaml", ".yml"}:
            value = yaml.safe_load(text)
        else:
            raise ValueError("Evidence receipts must be YAML (.yaml/.yml) or JSON (.json).")
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Evidence receipts are not valid YAML or JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError("Evidence receipts root must be an object/mapping.")
    return value


def _repository_root(path: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError("git is required for evidence receipt inspection") from exc

    if result.returncode != 0:
        raise ValueError("Evidence receipt inspection requires the contract to be in a Git worktree.")
    return Path(result.stdout.strip())


def _git_object_exists(repository_root: Path, object_name: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repository_root), "cat-file", "-e", object_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _validate_ref(ref: str) -> str | None:
    normalized = ref.rstrip("/")
    if not normalized or "\\" in normalized:
        return None
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        return None
    return normalized


def _field_value(contract: dict[str, Any], field: str) -> tuple[bool, Any]:
    value: Any = contract
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def _is_declared(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _applicable_evidence_fields(contract: dict[str, Any]) -> list[tuple[str, tuple[str, ...]]]:
    trace = build_rule_trace(contract)
    ordered_fields: list[str] = []
    rules_by_field: dict[str, list[str]] = {}

    for rule in trace.rules:
        if rule.status == TRACE_NOT_APPLICABLE:
            continue
        for field in rule.consumed_fields:
            if not field.startswith("evidence."):
                continue
            present, value = _field_value(contract, field)
            if not present or not _is_declared(value):
                continue
            if field not in rules_by_field:
                ordered_fields.append(field)
                rules_by_field[field] = []
            if rule.rule_id not in rules_by_field[field]:
                rules_by_field[field].append(rule.rule_id)

    # Avoid double-counting aggregate mappings such as evidence.checks when a more
    # specific consumed field beneath that mapping is already in the applicable set.
    selected: list[tuple[str, tuple[str, ...]]] = []
    for field in ordered_fields:
        prefix = f"{field}."
        if any(other.startswith(prefix) for other in ordered_fields):
            continue
        selected.append((field, tuple(rules_by_field[field])))
    return selected


def _parse_receipts(payload: dict[str, Any]) -> tuple[ContractBinding, str, tuple[EvidenceReceipt, ...]]:
    if payload.get("schema_version") != EVIDENCE_RECEIPTS_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported evidence receipts schema version: "
            f"{payload.get('schema_version')!r}."
        )
    if payload.get("type") != EVIDENCE_RECEIPTS_TYPE:
        raise ValueError(
            f"Evidence receipts type must be {EVIDENCE_RECEIPTS_TYPE!r}."
        )
    if payload.get("scientific_validation") is not False:
        raise ValueError("Evidence receipts must declare scientific_validation: false.")
    if payload.get("automatic_verification") is not False:
        raise ValueError("Evidence receipts must declare automatic_verification: false.")

    scope_notice = payload.get("scope_notice")
    if not isinstance(scope_notice, str) or "not verify" not in scope_notice.lower():
        raise ValueError(
            "Evidence receipts scope_notice must explicitly state that receipts do not verify support."
        )

    contract_meta = payload.get("contract")
    if not isinstance(contract_meta, dict):
        raise ValueError("Evidence receipts must contain contract metadata.")
    serialized_binding = contract_meta.get("input_binding")
    if not isinstance(serialized_binding, dict):
        raise ValueError("Evidence receipts must contain contract.input_binding.")
    binding = contract_binding_from_dict(serialized_binding)

    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError("Evidence receipts must contain snapshot metadata.")
    revision = snapshot.get("repository_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError(
            "snapshot.repository_revision must be a full lowercase 40-character Git SHA."
        )

    records = payload.get("receipts")
    if not isinstance(records, list):
        raise ValueError("Evidence receipts must contain a receipts list.")

    parsed: list[EvidenceReceipt] = []
    seen_fields: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Every evidence receipt must be an object/mapping.")
        field = record.get("field")
        refs = record.get("refs")
        note = record.get("note")
        if not isinstance(field, str) or not field.startswith("evidence."):
            raise ValueError("Evidence receipt field must be a non-empty evidence.* path.")
        if field in seen_fields:
            raise ValueError(f"Duplicate evidence receipt field: {field}")
        seen_fields.add(field)
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"Evidence receipt {field} must declare at least one ref.")
        if not all(isinstance(ref, str) and ref for ref in refs):
            raise ValueError(f"Evidence receipt {field} refs must be non-empty strings.")
        if len(refs) != len(set(refs)):
            raise ValueError(f"Evidence receipt {field} refs must be unique.")
        if note is not None and (not isinstance(note, str) or not note.strip()):
            raise ValueError(f"Evidence receipt {field} note must be a non-empty string or null.")
        parsed.append(EvidenceReceipt(field=field, refs=tuple(refs), note=note))

    return binding, revision, tuple(parsed)


def inspect_evidence_receipts(
    contract: dict[str, Any],
    receipts_payload: dict[str, Any],
    *,
    contract_path: str | Path,
) -> EvidenceReceiptInspection:
    saved_binding, revision, receipts = _parse_receipts(receipts_payload)
    current_binding = build_contract_binding(contract)

    contract_file = Path(contract_path)
    if str(contract_path) == "-":
        raise ValueError(
            "Evidence receipt inspection requires a contract file path, not stdin, "
            "because receipt refs are repository-relative."
        )
    repository_root = _repository_root(contract_file)
    revision_resolves = _git_object_exists(repository_root, f"{revision}^{{commit}}")

    missing_refs: list[str] = []
    invalid_refs: list[str] = []
    ref_resolution: dict[str, bool] = {}

    for receipt in receipts:
        if saved_binding == current_binding:
            present, _ = _field_value(contract, receipt.field)
            if not present:
                raise ValueError(
                    f"Evidence receipt field {receipt.field!r} does not exist in the supplied contract."
                )
        for ref in receipt.refs:
            if ref in ref_resolution:
                continue
            normalized = _validate_ref(ref)
            if normalized is None:
                invalid_refs.append(ref)
                ref_resolution[ref] = False
                continue
            resolves = bool(
                revision_resolves
                and _git_object_exists(repository_root, f"{revision}:{normalized}")
            )
            ref_resolution[ref] = resolves
            if revision_resolves and not resolves:
                missing_refs.append(ref)

    profile = str(contract.get("profile", DEFAULT_PROFILE))
    profile_manifest_binding = build_profile_manifest_binding(
        get_profile_manifest(profile).to_dict()
    )
    receipts_by_field = {receipt.field: receipt for receipt in receipts}
    applicable = _applicable_evidence_fields(contract)
    coverage: list[ReceiptCoverage] = []
    used_fields: set[str] = set()

    if saved_binding == current_binding:
        for field, rule_ids in applicable:
            receipt = receipts_by_field.get(field)
            if receipt is None:
                coverage.append(
                    ReceiptCoverage(
                        field=field,
                        status=UNRECEIPTED,
                        applicable_rule_ids=rule_ids,
                    )
                )
                continue

            used_fields.add(field)
            coverage.append(
                ReceiptCoverage(
                    field=field,
                    status=RECEIPTED,
                    applicable_rule_ids=rule_ids,
                    refs=receipt.refs,
                    refs_resolve=bool(
                        revision_resolves
                        and all(ref_resolution.get(ref, False) for ref in receipt.refs)
                    ),
                )
            )

    unused = tuple(
        receipt for receipt in receipts if receipt.field not in used_fields
    )

    return EvidenceReceiptInspection(
        saved_binding=saved_binding,
        current_binding=current_binding,
        profile=profile,
        profile_manifest_binding=profile_manifest_binding,
        repository_revision=revision,
        revision_resolves=revision_resolves,
        coverage=tuple(coverage),
        unused_receipts=unused,
        missing_refs=tuple(sorted(set(missing_refs))),
        invalid_refs=tuple(sorted(set(invalid_refs))),
    )


def format_evidence_receipt_inspection_text(
    inspection: EvidenceReceiptInspection,
) -> str:
    lines = [
        f"Contract binding: {'MATCH' if inspection.contract_binding_matches else 'MISMATCH'}",
        f"Snapshot revision: {inspection.repository_revision}",
        f"Snapshot resolves: {'true' if inspection.revision_resolves else 'false'}",
        f"Receipt integrity: {'OK' if inspection.integrity_ok else 'INVALID'}",
        "Scientific validation: false",
        "Automatic verification: false",
        "",
    ]

    if not inspection.contract_binding_matches:
        lines.append("Coverage: not evaluated because the receipt sidecar is bound to a different contract.")
    else:
        lines.append("Applicable evidence declarations:")
        for item in inspection.coverage:
            lines.append(f"  {item.field}: {item.status}")
            lines.append(f"    rules: {', '.join(item.applicable_rule_ids)}")
            if item.refs:
                lines.append(f"    refs: {', '.join(item.refs)}")
                lines.append(
                    f"    refs resolve: {'true' if item.refs_resolve else 'false'}"
                )

    if inspection.unused_receipts:
        lines.append("")
        lines.append("Unused receipts:")
        for receipt in inspection.unused_receipts:
            lines.append(f"  {receipt.field}: {', '.join(receipt.refs)}")

    if inspection.invalid_refs:
        lines.append("")
        for ref in inspection.invalid_refs:
            lines.append(f"Invalid ref: {ref!r}")
    if inspection.missing_refs:
        lines.append("")
        for ref in inspection.missing_refs:
            lines.append(
                f"Missing ref at {inspection.repository_revision}: {ref}"
            )

    lines.extend(
        [
            "",
            "Boundary: RECEIPTED means only that retained repository refs are declared and resolve.",
            "It does not establish that those refs prove or adequately support the declaration.",
        ]
    )
    return "\n".join(lines)
