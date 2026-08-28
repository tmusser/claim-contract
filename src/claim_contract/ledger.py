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


LEDGER_STATUSES = (
    "OPEN",
    "SUPPORT_MET",
    "REFUTE_MET",
    "INCONCLUSIVE",
    "RETIRED",
)

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

    @property
    def ok(self) -> bool:
        return self.revision_resolves and not self.missing_refs and not self.invalid_refs


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
    for claim in ledger["claims"]:
        if not isinstance(claim, dict):
            raise ValueError("Each ledger claim must be an object/mapping.")

        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError("Each ledger claim must have a non-empty string id.")

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
    if not isinstance(ledger_type, str) or not ledger_type:
        raise ValueError("Ledger must declare a non-empty type.")
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

        snapshot = provenance.get("context_snapshot")
        if not isinstance(snapshot, dict):
            raise ValueError(f"Claim {claim_id} is missing provenance.context_snapshot.")

        revision = snapshot.get("repository_revision")
        refs = snapshot.get("refs")
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
            raise ValueError(
                f"Claim {claim_id} provenance.context_snapshot.repository_revision "
                "must be a full 40-character Git SHA."
            )
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"Claim {claim_id} must declare provenance.context_snapshot.refs.")
        if not all(isinstance(ref, str) and ref for ref in refs):
            raise ValueError(f"Claim {claim_id} context refs must be non-empty strings.")

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

        results.append(
            ClaimProvenanceResult(
                claim_id=claim_id,
                revision=revision,
                refs=tuple(refs),
                revision_resolves=revision_resolves,
                missing_refs=tuple(missing_refs),
                invalid_refs=tuple(invalid_refs),
            )
        )

    return results
