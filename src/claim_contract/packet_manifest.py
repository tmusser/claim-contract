"""Portable, byte-bound snapshots of dedicated review packet directories."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote

import yaml

from .binding import build_contract_binding
from .io import load_contract
from .metadata import TOOL_NAME, TOOL_VERSION
from .packet_consistency import verify_packet_consistency
from .packet_links import check_packet_links, iter_packet_links

MANIFEST_NAME = "packet-manifest.json"
MANIFEST_TYPE = "claim_contract.packet_manifest"
SCOPE_NOTICE = (
    "Packet inventory, byte identity and declared contract/report bindings only. "
    "This does not authenticate the producer, establish review completeness, "
    "or scientifically validate evidence."
)
_DIGEST = re.compile(r"[0-9a-f]{64}")
_CONTRACT_SUFFIXES = {".yaml", ".yml", ".json"}


class ManifestFailure(ValueError):
    """A readable packet does not satisfy the manifest contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _portable_name(name: str) -> bool:
    return bool(name) and name not in {".", ".."} and not any(
        char in name for char in '\\:<>|"*?'
    ) and not any(ord(char) < 32 for char in name) and not name.endswith(
        (".", " ")
    ) and not PureWindowsPath(name).is_reserved()


def _scan(root: Path) -> dict[str, str]:
    """Hash all files without following symlinks or accepting special files."""
    files: dict[str, str] = {}
    names: set[str] = set()

    def raise_error(exc: OSError) -> None:
        raise exc

    for parent, directories, filenames in os.walk(root, onerror=raise_error):
        for name in sorted(directories + filenames):
            path = Path(parent) / name
            relative = path.relative_to(root).as_posix()
            if not _portable_name(name) or name.casefold() == ".git":
                raise ManifestFailure(f"Nonportable path: {relative}")
            if relative.casefold() in names:
                raise ManifestFailure(f"Case-insensitive path collision: {relative}")
            names.add(relative.casefold())
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ManifestFailure(f"Symlink is not portable: {relative}")
            if stat.S_ISDIR(mode):
                if relative.casefold() == MANIFEST_NAME.casefold():
                    raise ManifestFailure(f"Manifest path is a directory: {relative}")
                continue
            if not stat.S_ISREG(mode):
                raise ManifestFailure(f"Not a regular file: {relative}")
            if relative == MANIFEST_NAME:
                continue
            if relative.casefold() == MANIFEST_NAME.casefold():
                raise ManifestFailure(f"Reserved manifest filename: {relative}")
            files[relative] = _sha256(path)
    return dict(sorted(files.items()))


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestFailure(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ManifestFailure(f"Invalid JSON constant: {value}")


def _read_json(path: Path) -> dict:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicates,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict):
        raise ManifestFailure(f"Expected JSON object: {path.name}")
    return value


def _check_local_links(root: Path, inventory: dict[str, str]) -> None:
    """Check supported inline links in the entrypoint without reading outside it."""
    for line, _, target in iter_packet_links(root / "packet.md"):
        if not target or target.startswith("#"):
            continue
        if target.lower().startswith(("http:", "https:", "mailto:")):
            continue
        target = unquote(target.split("#", 1)[0])
        path = Path(target)
        if (
            path.is_absolute()
            or PureWindowsPath(target).anchor
            or "\\" in target
            or ":" in target
            or "?" in target
        ):
            raise ManifestFailure(f"Line {line}: nonportable link {target!r}")
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            raise ManifestFailure(f"Line {line}: link escapes packet: {target!r}")
        if resolved.relative_to(root).as_posix() not in inventory:
            raise ManifestFailure(f"Line {line}: local link is not a bundled file: {target!r}")


def _pairs(root: Path, inventory: dict[str, str]) -> list[dict]:
    pairs = []
    reports = set()
    for relative in inventory:
        path = Path(relative)
        if path.parts[0] != "contracts" or path.suffix.lower() not in _CONTRACT_SUFFIXES:
            continue
        report_path = (Path("validate") / Path(*path.parts[1:]).with_suffix(".json")).as_posix()
        if report_path not in inventory:
            raise ManifestFailure(f"Missing bound report for {relative}: {report_path}")
        if report_path in reports:
            raise ManifestFailure(f"Multiple contracts map to {report_path}")
        reports.add(report_path)
        binding = build_contract_binding(load_contract(root / relative)).to_dict()
        report = _read_json(root / report_path)
        metadata = report.get("contract")
        if (
            report.get("type") != "claim_contract.report"
            or report.get("schema_version") != "1.0"
            or not isinstance(metadata, dict)
            or metadata.get("input_binding") != binding
        ):
            raise ManifestFailure(f"Report does not bind to {relative}: {report_path}")
        pairs.append({
            "contract": relative,
            "report": report_path,
            "input_binding": binding,
            "profile_manifest_binding": metadata.get("profile_manifest_binding"),
        })
    actual_reports = {
        name for name in inventory
        if Path(name).parts[0] == "validate" and Path(name).suffix.lower() == ".json"
    }
    if not pairs:
        raise ManifestFailure("No returned contract/report pairs")
    if actual_reports != reports:
        raise ManifestFailure(f"Unpaired reports: {sorted(actual_reports - reports)}")
    return pairs


def _prepare(root: Path, inventory: dict[str, str]) -> list[dict]:
    if "packet.md" not in inventory:
        raise ManifestFailure("Missing packet.md")
    _check_local_links(root, inventory)
    pairs = _pairs(root, inventory)
    return pairs


def _root(folder: Path) -> Path:
    if not folder.is_dir():
        raise FileNotFoundError(f"Packet directory not found: {folder}")
    if folder.is_symlink():
        raise ManifestFailure("Packet directory must not be a symlink")
    return folder.resolve()


def create_manifest(folder: Path) -> dict:
    """Create once, after existing link and consistency gates succeed."""
    root = _root(folder)
    destination = root / MANIFEST_NAME
    if destination.exists() or destination.is_symlink():
        raise ManifestFailure(f"{MANIFEST_NAME} already exists; preserve it")
    inventory = _scan(root)
    pairs = _prepare(root, inventory)
    links = check_packet_links(root / "packet.md")
    if links:
        raise ManifestFailure(f"Packet link check failed: {links[0]}")
    consistency = verify_packet_consistency(root / "packet.md")
    if consistency.failures:
        failure = consistency.failures[0]
        raise ManifestFailure(
            f"Packet consistency check failed: line {failure.line}: "
            f"{failure.code}: {failure.reason}"
        )
    if _scan(root) != inventory:
        raise ManifestFailure("Packet changed during manifest creation")
    manifest = {
        "schema_version": "1.0",
        "type": MANIFEST_TYPE,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "scope_notice": SCOPE_NOTICE,
        "scientific_validation": False,
        "entrypoint": "packet.md",
        "artifacts": inventory,
        "contract_reports": pairs,
    }
    encoded = (json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    # No overwrite, including races with another creator.
    with destination.open("xb") as stream:
        stream.write(encoded)
    return {
        "manifest": MANIFEST_NAME,
        "manifest_sha256": hashlib.sha256(encoded).hexdigest(),
        "artifacts_checked": len(inventory),
        "failures": [],
    }


def verify_manifest(folder: Path, expected_sha256: str | None = None) -> dict:
    """Verify a copied packet without re-running potentially newer profile rules."""
    root = _root(folder)
    path = root / MANIFEST_NAME
    if not path.exists() or path.is_symlink() or not path.is_file():
        raise ManifestFailure(f"Missing or nonregular {MANIFEST_NAME}")
    inventory = _scan(root)
    digest = _sha256(path)
    manifest = _read_json(path)
    declared = manifest.get("artifacts")
    tool = manifest.get("tool")
    if (
        set(manifest) != {
            "schema_version", "type", "tool", "scope_notice", "scientific_validation",
            "entrypoint", "artifacts", "contract_reports",
        }
        or manifest.get("schema_version") != "1.0"
        or manifest.get("type") != MANIFEST_TYPE
        or manifest.get("scope_notice") != SCOPE_NOTICE
        or manifest.get("scientific_validation") is not False
        or manifest.get("entrypoint") != "packet.md"
        or not isinstance(tool, dict)
        or tool.get("name") != TOOL_NAME
        or not isinstance(tool.get("version"), str)
        or not isinstance(declared, dict)
        or not all(
            isinstance(value, str) and _DIGEST.fullmatch(value)
            for value in declared.values()
        )
        or not isinstance(manifest.get("contract_reports"), list)
    ):
        raise ManifestFailure("Malformed or unsupported packet manifest")
    failures = []
    if expected_sha256 is not None:
        if not _DIGEST.fullmatch(expected_sha256):
            raise ValueError("Expected manifest SHA-256 must be 64 lowercase hex characters")
        if digest != expected_sha256:
            failures.append({"code": "MANIFEST_DIGEST_MISMATCH", "path": MANIFEST_NAME})
    for relative in sorted(declared.keys() - inventory.keys()):
        failures.append({"code": "MISSING_ARTIFACT", "path": relative})
    for relative in sorted(inventory.keys() - declared.keys()):
        failures.append({"code": "EXTRA_ARTIFACT", "path": relative})
    for relative in sorted(declared.keys() & inventory.keys()):
        if declared[relative] != inventory[relative]:
            failures.append({"code": "MODIFIED_ARTIFACT", "path": relative})
    if not failures:
        pairs = _prepare(root, inventory)
        # Strict JSON comparison avoids treating false and 0 as equivalent.
        if json.dumps(pairs, sort_keys=True, allow_nan=False) != json.dumps(
            manifest["contract_reports"], sort_keys=True, allow_nan=False
        ):
            failures.append({"code": "CONTRACT_REPORT_METADATA_MISMATCH", "path": MANIFEST_NAME})
    return {
        "manifest": MANIFEST_NAME,
        "manifest_sha256": digest,
        "artifacts_checked": len(inventory),
        "failures": failures,
    }


INPUT_EXCEPTIONS = (OSError, ValueError, TypeError, KeyError, RecursionError, yaml.YAMLError)
