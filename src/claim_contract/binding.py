from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

HASH_ALGORITHM = "sha256"
CANONICALIZATION = "parsed-contract-v1"
PROFILE_MANIFEST_CANONICALIZATION = "profile-manifest-semantics-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ContractBinding:
    """Deterministic identity for the parsed contract that produced a report."""

    algorithm: str
    canonicalization: str
    contract_sha256: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def matches_contract(self, contract: Mapping[str, Any]) -> bool:
        return self == build_contract_binding(contract)


@dataclass(frozen=True)
class ProfileManifestBinding:
    """Deterministic identity for the profile semantics used by a report."""

    algorithm: str
    canonicalization: str
    profile_manifest_sha256: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def matches_manifest(self, manifest_identity: Mapping[str, Any]) -> bool:
        return self == build_profile_manifest_binding(manifest_identity)


def build_contract_binding(contract: Mapping[str, Any]) -> ContractBinding:
    """Build a deterministic binding over parsed contract content.

    Mapping key order and source formatting do not affect the fingerprint. Any
    semantic value change in the parsed contract does.
    """

    if not isinstance(contract, Mapping):
        raise TypeError("Contract binding requires a mapping/object.")

    return ContractBinding(
        algorithm=HASH_ALGORITHM,
        canonicalization=CANONICALIZATION,
        contract_sha256=_sha256_mapping(contract),
    )


def build_profile_manifest_binding(
    manifest_identity: Mapping[str, Any],
) -> ProfileManifestBinding:
    """Build a deterministic binding over profile-manifest semantics.

    Callers should pass the manifest's semantic identity payload rather than the
    presentation envelope so implementation-release metadata such as tool.version
    does not cause ruleset drift when the profile itself is unchanged.
    """

    if not isinstance(manifest_identity, Mapping):
        raise TypeError("Profile manifest binding requires a mapping/object.")

    return ProfileManifestBinding(
        algorithm=HASH_ALGORITHM,
        canonicalization=PROFILE_MANIFEST_CANONICALIZATION,
        profile_manifest_sha256=_sha256_mapping(manifest_identity),
    )


def contract_binding_from_dict(payload: Mapping[str, Any]) -> ContractBinding:
    """Parse and validate a serialized contract binding."""

    algorithm = payload.get("algorithm")
    canonicalization = payload.get("canonicalization")
    contract_sha256 = payload.get("contract_sha256")

    if algorithm != HASH_ALGORITHM:
        raise ValueError(f"Unsupported contract-binding algorithm: {algorithm!r}")
    if canonicalization != CANONICALIZATION:
        raise ValueError(
            "Unsupported contract-binding canonicalization: "
            f"{canonicalization!r}"
        )
    if not isinstance(contract_sha256, str) or not _SHA256_RE.fullmatch(
        contract_sha256
    ):
        raise ValueError("contract_sha256 must be 64 lowercase hexadecimal characters.")

    return ContractBinding(
        algorithm=algorithm,
        canonicalization=canonicalization,
        contract_sha256=contract_sha256,
    )


def profile_manifest_binding_from_dict(
    payload: Mapping[str, Any],
) -> ProfileManifestBinding:
    """Parse and validate a serialized profile-manifest binding."""

    algorithm = payload.get("algorithm")
    canonicalization = payload.get("canonicalization")
    profile_manifest_sha256 = payload.get("profile_manifest_sha256")

    if algorithm != HASH_ALGORITHM:
        raise ValueError(f"Unsupported profile-binding algorithm: {algorithm!r}")
    if canonicalization != PROFILE_MANIFEST_CANONICALIZATION:
        raise ValueError(
            "Unsupported profile-binding canonicalization: "
            f"{canonicalization!r}"
        )
    if not isinstance(profile_manifest_sha256, str) or not _SHA256_RE.fullmatch(
        profile_manifest_sha256
    ):
        raise ValueError(
            "profile_manifest_sha256 must be 64 lowercase hexadecimal characters."
        )

    return ProfileManifestBinding(
        algorithm=algorithm,
        canonicalization=canonicalization,
        profile_manifest_sha256=profile_manifest_sha256,
    )


def _sha256_mapping(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        items = [
            [_normalize(key), _normalize(nested)]
            for key, nested in value.items()
        ]
        items.sort(key=lambda item: _sort_key(item[0]))
        return {"__mapping__": items}

    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]

    if isinstance(value, (set, frozenset)):
        items = [_normalize(item) for item in value]
        items.sort(key=_sort_key)
        return {"__set__": items}

    if value is None or isinstance(value, (bool, int, str)):
        return value

    if isinstance(value, float):
        if math.isnan(value):
            return {"__float__": "nan"}
        if math.isinf(value):
            return {"__float__": "inf" if value > 0 else "-inf"}
        return value

    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}

    if isinstance(value, (datetime, date, time)):
        return {"__datetime__": value.isoformat()}

    if isinstance(value, timedelta):
        return {"__timedelta__": str(value)}

    item = getattr(value, "item", None)
    if callable(item):
        try:
            converted = item()
        except (TypeError, ValueError):
            converted = value
        if converted is not value:
            return _normalize(converted)

    return {
        "__repr__": repr(value),
        "__type__": f"{type(value).__module__}.{type(value).__qualname__}",
    }


def _sort_key(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
