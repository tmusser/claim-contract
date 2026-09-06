from __future__ import annotations

import re
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .metadata import (
    LEDGER_INSPECTION_SCHEMA_VERSION,
    LEDGER_INSPECTION_TYPE,
    TOOL_NAME,
    TOOL_VERSION,
)


LEDGER_TYPE = "claim_contract.claim_ledger"
LEDGER_STATUSES = (
    "OPEN",
    "SUPPORT_MET",
    "REFUTE_MET",
    "INCONCLUSIVE",
    "RETIRED",
)
_ADJUDICATED_STATUSES = {"SUPPORT_MET", "REFUTE_MET", "INCONCLUSIVE"}

LEDGER_INSPECTION_NOTICE = (
    "Inspection exposes recorded ledger fields only. It does not evaluate support_if, "
    "refute_if, evidence, or whether any status should change, and it does not mutate "
    "the ledger."
)


@dataclass(frozen=True)
class ClaimProvenanceResult:
    claim_id: str
    revision: str
    refs: tuple[str, ...]
    revision_resolves: bool
    missing_refs: tuple[str, ...] = ()
    invalid_refs: tuple[str, ...] = ()
    judgment_revision: str | None = None
    judgment_refs: tuple[str, ...] = ()
    judgment_revision_resolves: bool | None = None
    judgment_missing_refs: tuple[str, ...] = ()
    judgment_invalid_refs: tuple[str, ...] = ()

    @property
    def creation_ok(self) -> bool:
        return self.revision_resolves and not self.missing_refs and not self.invalid_refs

    @property
    def judgment_ok(self) -> bool | None:
        if self.judgment_revision is None:
            return None
        return bool(
            self.judgment_revision_resolves
            and not self.judgment_missing_refs
            and not self.judgment_invalid_refs
        )

    @property
    def ok(self) -> bool:
        return self.creation_ok and self.judgment_ok is not False


@dataclass(frozen=True)
class LedgerInspection:
    mode: str
    ledger_schema_version: str
    ledger_type: str
    scope_notice: str
    claims: tuple[dict[str, Any], ...]
    status_filter: str | None = None
    claim_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": LEDGER_INSPECTION_SCHEMA_VERSION,
            "type": LEDGER_INSPECTION_TYPE,
            "tool": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
            },
            "ledger": {
                "schema_version": self.ledger_schema_version,
                "type": self.ledger_type,
                "scope_notice": self.scope_notice,
            },
            "inspection": {
                "mode": self.mode,
                "status_filter": self.status_filter,
                "claim_id": self.claim_id,
                "automatic_adjudication": False,
                "mutates_ledger": False,
                "notice": LEDGER_INSPECTION_NOTICE,
            },
            "count": len(self.claims),
            "claims": [deepcopy(claim) for claim in self.claims],
        }


def _load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Ledger file not found: {path}")

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Ledger root must be an object/mapping.")
    if not isinstance(value.get("claims"), list):
        raise ValueError("Ledger must contain a claims list.")
    return value


def _inspection_claims(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for claim in ledger["claims"]:
        if not isinstance(claim, dict):
            raise ValueError("Each ledger claim must be an object/mapping.")

        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError("Each ledger claim must have a non-empty string id.")
        if claim_id in seen_ids:
            raise ValueError(f"Ledger contains duplicate claim id: {claim_id}")
        seen_ids.add(claim_id)

        status = claim.get("status")
        if status not in LEDGER_STATUSES:
            raise ValueError(
                f"Claim {claim_id} has unsupported status {status!r}; "
                f"expected one of {', '.join(LEDGER_STATUSES)}."
            )
        claims.append(claim)
    return claims


def inspect_ledger(
    path: str | Path,
    *,
    status: str | None = None,
    claim_id: str | None = None,
) -> LedgerInspection:
    if status is not None and claim_id is not None:
        raise ValueError("Ledger inspection cannot combine status filtering with claim lookup.")
    if status is not None and status not in LEDGER_STATUSES:
        raise ValueError(
            f"Unsupported ledger status {status!r}; expected one of "
            f"{', '.join(LEDGER_STATUSES)}."
        )

    ledger = _load_ledger(Path(path))
    ledger_schema_version = ledger.get("schema_version")
    ledger_type = ledger.get("type")
    scope_notice = ledger.get("scope_notice")
    if not isinstance(ledger_schema_version, str) or not ledger_schema_version:
        raise ValueError("Ledger must declare a non-empty schema_version.")
    if ledger_type != LEDGER_TYPE:
        raise ValueError(f"Ledger type must be {LEDGER_TYPE!r}.")
    if not isinstance(scope_notice, str) or not scope_notice:
        raise ValueError("Ledger must declare a non-empty scope_notice.")

    claims = _inspection_claims(ledger)
    mode = "show" if claim_id is not None else "list"

    if claim_id is not None:
        selected = [claim for claim in claims if claim["id"] == claim_id]
        if not selected:
            raise ValueError(f"Ledger claim not found: {claim_id}")
    elif status is not None:
        selected = [claim for claim in claims if claim["status"] == status]
    else:
        selected = claims

    return LedgerInspection(
        mode=mode,
        ledger_schema_version=ledger_schema_version,
        ledger_type=ledger_type,
        scope_notice=scope_notice,
        claims=tuple(deepcopy(selected)),
        status_filter=status,
        claim_id=claim_id,
    )


def _repository_root(path: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError("git is required for ledger provenance verification") from exc

    if result.returncode != 0:
        raise ValueError("Ledger provenance verification requires a Git worktree.")
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
    if not normalized:
        return None

    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        return None
    return normalized


def _verify_snapshot(
    repository_root: Path,
    *,
    claim_id: str,
    field_path: str,
    snapshot: dict[str, Any],
) -> tuple[str, tuple[str, ...], bool, tuple[str, ...], tuple[str, ...]]:
    revision = snapshot.get("repository_revision")
    refs = snapshot.get("refs")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
        raise ValueError(
            f"Claim {claim_id} {field_path}.repository_revision must be a full "
            "40-character Git SHA."
        )
    if not isinstance(refs, list) or not refs:
        raise ValueError(f"Claim {claim_id} must declare {field_path}.refs.")
    if not all(isinstance(ref, str) and ref for ref in refs):
        raise ValueError(f"Claim {claim_id} {field_path} refs must be non-empty strings.")

    revision_resolves = _git_object_exists(repository_root, f"{revision}^{{commit}}")
    missing_refs: list[str] = []
    invalid_refs: list[str] = []

    if revision_resolves:
        for ref in refs:
            normalized = _validate_ref(ref)
            if normalized is None:
                invalid_refs.append(ref)
                continue
            if not _git_object_exists(repository_root, f"{revision}:{normalized}"):
                missing_refs.append(ref)

    return (
        revision,
        tuple(refs),
        revision_resolves,
        tuple(missing_refs),
        tuple(invalid_refs),
    )


def verify_pinned_provenance(path: str | Path) -> list[ClaimProvenanceResult]:
    ledger_path = Path(path)
    ledger = _load_ledger(ledger_path)
    repository_root = _repository_root(ledger_path)

    results: list[ClaimProvenanceResult] = []
    for claim in ledger["claims"]:
        if not isinstance(claim, dict):
            raise ValueError("Each ledger claim must be an object/mapping.")

        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError("Each ledger claim must have a non-empty string id.")

        provenance = claim.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError(f"Claim {claim_id} is missing provenance.")

        context_snapshot = provenance.get("context_snapshot")
        if not isinstance(context_snapshot, dict):
            raise ValueError(f"Claim {claim_id} is missing provenance.context_snapshot.")

        (
            revision,
            refs,
            revision_resolves,
            missing_refs,
            invalid_refs,
        ) = _verify_snapshot(
            repository_root,
            claim_id=claim_id,
            field_path="provenance.context_snapshot",
            snapshot=context_snapshot,
        )

        status = claim.get("status")
        judgment_revision = None
        judgment_refs: tuple[str, ...] = ()
        judgment_revision_resolves = None
        judgment_missing_refs: tuple[str, ...] = ()
        judgment_invalid_refs: tuple[str, ...] = ()

        judgment = claim.get("judgment")
        if judgment is not None and not isinstance(judgment, dict):
            raise ValueError(f"Claim {claim_id} judgment must be an object/mapping.")

        evidence_snapshot = (
            judgment.get("evidence_snapshot") if isinstance(judgment, dict) else None
        )
        if status in _ADJUDICATED_STATUSES and evidence_snapshot is None:
            raise ValueError(
                f"Claim {claim_id} status {status} requires judgment.evidence_snapshot."
            )
        if status == "OPEN" and evidence_snapshot is not None:
            raise ValueError(
                f"Claim {claim_id} status OPEN cannot carry judgment.evidence_snapshot."
            )

        if evidence_snapshot is not None:
            if not isinstance(evidence_snapshot, dict):
                raise ValueError(
                    f"Claim {claim_id} judgment.evidence_snapshot must be an object/mapping."
                )
            readable_refs = judgment.get("evidence_refs") if isinstance(judgment, dict) else None
            if readable_refs is not None:
                if not isinstance(readable_refs, list) or not all(
                    isinstance(ref, str) and ref for ref in readable_refs
                ):
                    raise ValueError(
                        f"Claim {claim_id} judgment.evidence_refs must be a string list."
                    )
                if readable_refs != evidence_snapshot.get("refs"):
                    raise ValueError(
                        f"Claim {claim_id} judgment.evidence_refs must exactly match "
                        "judgment.evidence_snapshot.refs."
                    )

            (
                judgment_revision,
                judgment_refs,
                judgment_revision_resolves,
                judgment_missing_refs,
                judgment_invalid_refs,
            ) = _verify_snapshot(
                repository_root,
                claim_id=claim_id,
                field_path="judgment.evidence_snapshot",
                snapshot=evidence_snapshot,
            )

        results.append(
            ClaimProvenanceResult(
                claim_id=claim_id,
                revision=revision,
                refs=refs,
                revision_resolves=revision_resolves,
                missing_refs=missing_refs,
                invalid_refs=invalid_refs,
                judgment_revision=judgment_revision,
                judgment_refs=judgment_refs,
                judgment_revision_resolves=judgment_revision_resolves,
                judgment_missing_refs=judgment_missing_refs,
                judgment_invalid_refs=judgment_invalid_refs,
            )
        )

    return results
