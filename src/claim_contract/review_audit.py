"""Reconcile a caller-retained structured assignment with receiver work records.

Record coverage is not analytical verification or workflow acceptance.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath

import yaml

from .metadata import TOOL_NAME, TOOL_VERSION

SCOPE_NOTICE = (
    "Assigned-work record coverage and artifact presence only. This does not "
    "prove that an inspection was performed, evaluate answer quality, establish "
    "workflow acceptance, or scientifically validate evidence."
)
FOCUS = ("wording", "denominator", "coverage")
RECORD_NAME = "review-work.json"
CONTRACT_SUFFIXES = {".yaml", ".yml", ".json"}


class AuditInputError(ValueError):
    """Caller input cannot establish the expected assignment."""


class UniqueLoader(yaml.SafeLoader):
    """Reject ambiguous duplicate mapping keys in the caller's assignment."""


def _unique_yaml(loader, node):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise AuditInputError(f"Duplicate task key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_yaml
)


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate work-record key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"Invalid JSON constant: {value}")


def _nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def _relative(value):
    if not _nonblank(value) or "\\" in value or ":" in value or "\x00" in value:
        raise ValueError("Expected an exact relative POSIX file path")
    path = PurePosixPath(value)
    if (
        path.is_absolute() or PureWindowsPath(value).anchor
        or any(part in {".", ".."} for part in value.split("/"))
        or path.as_posix() != value
    ):
        raise ValueError(f"Invalid relative path: {value!r}")
    return path


def _file(root, relative):
    """Return a regular file under root, without traversing symlink components."""
    path = root
    for part in _relative(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Symlink is not allowed: {relative}")
    if not path.is_file():
        raise ValueError(f"Missing regular file: {relative}")
    return path


def _inventory(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"Expected a regular directory: {root}")
    paths = set()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink is not allowed: {path.relative_to(root)}")
        if path.is_file() and path.suffix.lower() in CONTRACT_SUFFIXES:
            relative = path.relative_to(root).as_posix()
            _relative(relative)
            paths.add(relative)
    return paths


def _string_list(value, name, *, nonempty=False):
    if not isinstance(value, list) or not all(_nonblank(x) for x in value):
        raise AuditInputError(f"{name} must be a list of nonblank strings")
    if nonempty and not value:
        raise AuditInputError(f"{name} must not be empty")
    return value


def _assignment(task_bytes, baseline):
    task = yaml.load(task_bytes.decode("utf-8"), Loader=UniqueLoader)
    if not isinstance(task, dict) or not _nonblank(task.get("objective")):
        raise AuditInputError("Structured task must declare a nonblank objective")
    scope = task.get("scope")
    if not isinstance(scope, dict):
        raise AuditInputError("Task must declare scope")
    mode = scope.get("mode", "targeted")
    if mode not in ("targeted", "full", "delta"):
        raise AuditInputError("Unsupported scope.mode")
    locators = scope.get("source_locators")
    if locators != "all":
        _string_list(locators, "scope.source_locators", nonempty=True)
    if mode == "delta":
        if not _nonblank(scope.get("previous_review")):
            raise AuditInputError("Delta scope requires previous_review")
        _string_list(scope.get("change_context"), "scope.change_context", nonempty=True)

    inventory = _inventory(baseline)
    selected = scope.get("contracts")
    if selected == "all" and mode == "full":
        contracts = sorted(inventory)
    else:
        contracts = _string_list(selected, "scope.contracts", nonempty=True)
        if len(set(contracts)) != len(contracts):
            raise AuditInputError("Duplicate selected contracts")
        if mode == "full":
            raise AuditInputError("Full mode requires scope.contracts: all")
        for relative in contracts:
            _relative(relative)
            if relative not in inventory:
                raise AuditInputError(f"Selected contract not in retained baseline: {relative}")
    if not contracts:
        raise AuditInputError("Selected baseline inventory is empty")
    focus = _string_list(task.get("focus", list(FOCUS)), "focus")
    if len(set(focus)) != len(focus) or any(x not in FOCUS for x in focus):
        raise AuditInputError("focus contains unknown or duplicate checks")
    questions = _string_list(task.get("questions", []), "questions")
    return contracts, focus, questions


def _expected(contracts, focus, questions):
    records = {}
    for contract in contracts:
        for check in FOCUS:
            key = ("focus", contract, check)
            records[key] = {
                "kind": "focus", "contract": contract, "check": check,
                "requested": check in focus,
            }
    for index, question in enumerate(questions, 1):
        records[("question", index)] = {
            "kind": "question", "index": index, "question": question,
            "requested": True,
        }
    return records


def _key(record):
    if not isinstance(record, dict):
        raise ValueError("Expected work record object")
    if record.get("kind") == "focus":
        contract, check = record.get("contract"), record.get("check")
        if not _nonblank(contract) or not _nonblank(check):
            raise ValueError("Focus record requires contract and check")
        return ("focus", contract, check)
    if record.get("kind") == "question":
        index = record.get("index")
        if type(index) is not int or index < 1:
            raise ValueError("Question index must be a positive integer")
        return ("question", index)
    raise ValueError("Unknown work record kind")


def audit_review(packet: Path, task: Path, baseline: Path) -> dict:
    """Audit declared focus/question records against independent caller inputs."""
    if not packet.is_dir() or packet.is_symlink():
        raise AuditInputError("Packet must be a regular directory")
    root = packet.resolve()
    if baseline.is_symlink() or task.is_symlink():
        raise AuditInputError("Caller task and baseline must not be symlinks")
    task, baseline = task.resolve(), baseline.resolve()
    if task.is_relative_to(root) or baseline.is_relative_to(root):
        raise AuditInputError("Caller-retained task and baseline must be outside the packet")
    if root.is_relative_to(baseline):
        raise AuditInputError("Packet must be outside the retained baseline")
    task_bytes = task.read_bytes()
    contracts, focus, questions = _assignment(task_bytes, baseline)
    expected = _expected(contracts, focus, questions)
    failures = []

    def fail(code, target, reason):
        failures.append({"code": code, "target": target, "reason": reason})

    try:
        if _file(root, "task.md").read_bytes() != task_bytes:
            fail("TASK_DRIFT", "task.md", "Retained task differs from caller assignment")
    except (OSError, ValueError) as exc:
        fail("TASK_SNAPSHOT", "task.md", str(exc))

    try:
        returned = _inventory(root / "contracts")
    except (OSError, ValueError) as exc:
        returned = set()
        fail("RETURNED_INVENTORY", "contracts", str(exc))
    for contract in sorted(set(contracts) - returned):
        fail("MISSING_CONTRACT", contract, "Selected contract was not returned")
    for contract in sorted(returned - set(contracts)):
        fail("EXTRA_CONTRACT", contract, "Returned contract outside caller selection")

    ledger = {}
    try:
        ledger = json.loads(
            _file(root, RECORD_NAME).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json, parse_constant=_reject_constant,
        )
        if (
            not isinstance(ledger, dict)
            or set(ledger) != {"schema_version", "type", "work_status", "records"}
            or ledger.get("schema_version") != "1.0"
            or ledger.get("type") != "claim_contract.review_work"
            or ledger.get("work_status") not in ("complete", "partial", "blocked")
            or not isinstance(ledger.get("records"), list)
        ):
            raise ValueError("Malformed or unsupported review work record")
    except (OSError, ValueError, RecursionError) as exc:
        fail("WORK_RECORD_INPUT", RECORD_NAME, str(exc))
        ledger = {}

    seen = {}
    duplicates = set()
    for number, record in enumerate(ledger.get("records", []), 1):
        try:
            key = _key(record)
        except ValueError as exc:
            fail("INVALID_RECORD", f"records[{number}]", str(exc))
            continue
        if key not in expected:
            fail("UNEXPECTED_RECORD", repr(key), "Not in caller's expected record inventory")
            continue
        if key in seen:
            fail("DUPLICATE_RECORD", repr(key), "Multiple records for the same requested/check slot")
            duplicates.add(key)
            continue
        seen[key] = record

    rows = []
    counts = {
        "completed": 0, "blocked": 0, "not_completed": 0, "not_requested": 0,
    }
    for key, item in expected.items():
        record = seen.get(key)
        target = repr(key)
        status = "not_completed" if item["requested"] else "not_requested"
        if record is None:
            fail("MISSING_RECORD", target, "Expected explicit work record")
        elif key not in duplicates:
            errors_before = len(failures)
            supplied = record.get("status")
            allowed = ("completed", "blocked") if item["requested"] else ("not_requested",)
            required = (
                {"kind", "contract", "check", "status", "artifact", "detail"}
                if item["kind"] == "focus" else
                {"kind", "index", "question", "status", "artifact", "detail"}
            )
            if set(record) != required:
                fail("RECORD_FIELDS", target, "Expected exactly the documented work-record fields")
            if item["kind"] == "question" and record.get("question") != item["question"]:
                fail("QUESTION_DRIFT", target, "Question text differs from caller assignment")
            if supplied not in allowed:
                fail("STATUS_MISMATCH", target, "Status does not match requested scope")
            detail = record.get("detail")
            artifact = record.get("artifact")
            if not _nonblank(detail):
                fail("MISSING_DETAIL", target, "Record needs a result, answer, or reason")
            if supplied == "completed":
                try:
                    if artifact in (RECORD_NAME, "task.md", "packet-manifest.json"):
                        raise ValueError("Assignment/manifest/work record cannot support its own completion")
                    support = _file(root, artifact)
                    if support.stat().st_size == 0:
                        raise ValueError("Supporting artifact is empty")
                except (OSError, ValueError, TypeError) as exc:
                    fail("MISSING_SUPPORT", target, str(exc))
                if item["kind"] == "focus" and item["contract"] not in returned:
                    fail("COMPLETION_WITHOUT_CONTRACT", target, "Selected contract was not returned")
            elif artifact is not None:
                try:
                    _file(root, artifact)
                except (OSError, ValueError, TypeError) as exc:
                    fail("INVALID_SUPPORT", target, str(exc))
                if supplied == "not_requested":
                    fail("STATUS_MISMATCH", target, "Unrequested work must have null artifact")
            if len(failures) == errors_before:
                status = supplied
                if supplied == "blocked":
                    fail("REQUEST_BLOCKED", target, detail)
        rows.append({
            **item, "status": status,
            "artifact": record.get("artifact") if record and isinstance(record.get("artifact"), str) else None,
            "detail": record.get("detail") if record and isinstance(record.get("detail"), str) else None,
        })
        counts[status] += 1

    requested = len(contracts) * len(focus) + len(questions)
    # This is only the derived status of assigned inspection records; existing
    # baseline, report, consistency and reviewer gates still govern acceptance.
    if counts["completed"] == requested and not failures:
        derived_status = "complete"
    elif counts["completed"]:
        derived_status = "partial"
    else:
        derived_status = "blocked"
    if ledger and ledger.get("work_status") != derived_status:
        fail("WORK_STATUS_MISMATCH", RECORD_NAME, f"Declared {ledger['work_status']}; derived {derived_status}")
    return {
        "schema_version": "1.0",
        "type": "claim_contract.review_work_audit",
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "scope_notice": SCOPE_NOTICE,
        "scientific_validation": False,
        "analytical_completion_verified": False,
        "selected_contracts": contracts,
        "requested_count": requested,
        "counts": counts,
        "recorded_status": ledger.get("work_status"),
        "derived_status": derived_status,
        "records": rows,
        "failures": failures,
    }
