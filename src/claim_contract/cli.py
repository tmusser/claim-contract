from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from .binding import build_contract_binding, contract_binding_from_dict
from .formatters import format_json, format_json_error, format_text
from .handoff import build_chart_handoff, handoff_exit_code
from .io import load_contract
from .ledger import verify_pinned_provenance
from .metadata import (
    REPORT_SCHEMA_VERSION,
    REPORT_TYPE,
    TOOL_NAME,
    TOOL_VERSION,
)
from .models import Verdict
from .profiles import ProfileManifest, get_profile_manifest
from .validator import validate_contract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Validate a declared minimum contract for an analytical claim.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{TOOL_NAME} {TOOL_VERSION}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a YAML or JSON contract.")
    validate.add_argument("contract", help="Path to the contract file.")
    output = validate.add_mutually_exclusive_group()
    output.add_argument(
        "--format",
        choices=("text", "json"),
        dest="format",
        help="Output format.",
    )
    output.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="Shortcut for --format json.",
    )
    validate.set_defaults(format="text")
    validate.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Exit 1 for REVIEW as well as BLOCK.",
    )

    handoff = subparsers.add_parser(
        "handoff",
        help="Emit bounded downstream handoff artifacts.",
    )
    handoff_commands = handoff.add_subparsers(dest="handoff_command", required=True)
    chart_handoff = handoff_commands.add_parser(
        "chart",
        help="Emit a bounded JSON claim context for chart-contract.",
    )
    chart_handoff.add_argument("contract", help="Path to the YAML or JSON contract.")
    chart_handoff.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Exit 1 for REVIEW as well as BLOCK while still emitting the handoff.",
    )

    profile = subparsers.add_parser(
        "profile",
        help="Inspect versioned validation-profile metadata.",
    )
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_show = profile_commands.add_parser(
        "show",
        help="Show the machine-readable rule manifest for a profile.",
    )
    profile_show.add_argument("profile", help="Profile name, for example minimum-v0.1.")
    profile_output = profile_show.add_mutually_exclusive_group()
    profile_output.add_argument(
        "--format",
        choices=("text", "json"),
        dest="format",
        help="Output format.",
    )
    profile_output.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="Shortcut for --format json.",
    )
    profile_show.set_defaults(format="text")

    ledger = subparsers.add_parser(
        "ledger",
        help="Inspect repository claim-ledger metadata.",
    )
    ledger_commands = ledger.add_subparsers(dest="ledger_command", required=True)
    ledger_verify = ledger_commands.add_parser(
        "verify",
        help="Verify commit-pinned ledger context references.",
    )
    ledger_verify.add_argument("ledger", help="Path to claims/ledger.yaml or equivalent.")

    report = subparsers.add_parser(
        "report",
        help="Inspect durable validation reports.",
    )
    report_commands = report.add_subparsers(dest="report_command", required=True)
    report_verify = report_commands.add_parser(
        "verify",
        help="Verify that a saved JSON report is bound to a contract.",
    )
    report_verify.add_argument("report", help="Path to a saved JSON validation report.")
    report_verify.add_argument(
        "--contract",
        required=True,
        help="Current YAML or JSON contract to compare with the saved report binding.",
    )

    return parser


def _format_profile_text(manifest: ProfileManifest) -> str:
    lines = [
        f"Profile: {manifest.name}",
        f"Rules: {len(manifest.rules)}",
        "Scientific validation: false",
        "",
    ]
    for rule in manifest.rules:
        lines.extend(
            [
                f"{rule.rule_id} {rule.severity.value}",
                f"  Trigger: {rule.trigger}",
                f"  Consumes: {', '.join(rule.consumed_fields)}",
                f"  Boundary: {rule.known_boundary}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _run_profile_show(name: str, output_format: str) -> int:
    try:
        manifest = get_profile_manifest(name)
    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    if output_format == "json":
        print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    else:
        print(_format_profile_text(manifest))
    return 0


def _run_chart_handoff(contract_path: str, warnings_as_errors: bool) -> int:
    try:
        contract = load_contract(contract_path)
        handoff = build_chart_handoff(contract)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(format_json_error(f"Input error: {exc}"))
        return 2

    print(json.dumps(handoff.to_dict(), indent=2, sort_keys=True))
    return handoff_exit_code(handoff, warnings_as_errors=warnings_as_errors)


def _run_ledger_verify(path: str) -> int:
    try:
        results = verify_pinned_provenance(path)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    failed = False
    for result in results:
        if result.ok:
            print(f"{result.claim_id}: OK")
            print(f"  revision {result.revision} resolves")
            print(f"  {len(result.refs)} ref(s) resolved")
            continue

        failed = True
        print(f"{result.claim_id}: INVALID")
        if not result.revision_resolves:
            print(
                f"  revision {result.revision} is not available in the local repository"
            )
            continue

        for ref in result.invalid_refs:
            print(f"  ref {ref!r} is not a safe repository-relative path")
        for ref in result.missing_refs:
            print(f"  ref {ref} not found at {result.revision}")

    return 1 if failed else 0


def _load_report_payload(path: str) -> dict[str, object]:
    report_path = Path(path)
    if report_path.suffix.lower() != ".json":
        raise ValueError("Saved report must be JSON (.json).")
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Report file is not valid JSON: {report_path}: {exc.msg}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError("Report root must be an object/mapping.")
    return payload


def _run_report_verify(report_path: str, contract_path: str) -> int:
    try:
        payload = _load_report_payload(report_path)
        if payload.get("type") != REPORT_TYPE:
            raise ValueError(
                f"Expected report type {REPORT_TYPE!r}; got {payload.get('type')!r}."
            )
        if payload.get("schema_version") != REPORT_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported report schema version: "
                f"{payload.get('schema_version')!r}."
            )

        contract_metadata = payload.get("contract")
        if not isinstance(contract_metadata, Mapping):
            raise ValueError("Report does not contain contract metadata.")
        serialized_binding = contract_metadata.get("input_binding")
        if not isinstance(serialized_binding, Mapping):
            raise ValueError("Report does not contain contract.input_binding.")

        binding = contract_binding_from_dict(serialized_binding)
        contract = load_contract(contract_path)
        candidate = build_contract_binding(contract)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    matches = binding == candidate
    print(f"Binding: {'MATCH' if matches else 'MISMATCH'}")
    print(f"Contract SHA-256: {'MATCH' if matches else 'MISMATCH'}")
    print(f"Saved SHA-256: {binding.contract_sha256}")
    print(f"Current SHA-256: {candidate.contract_sha256}")
    if "version" in contract_metadata:
        print(f"Bound contract version: {contract_metadata['version']}")
    if "profile" in contract_metadata:
        print(f"Bound profile: {contract_metadata['profile']}")
    return 0 if matches else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "handoff":
        return _run_chart_handoff(args.contract, args.warnings_as_errors)
    if args.command == "profile":
        return _run_profile_show(args.profile, args.format)
    if args.command == "ledger":
        return _run_ledger_verify(args.ledger)
    if args.command == "report":
        return _run_report_verify(args.report, args.contract)

    try:
        contract = load_contract(args.contract)
        report = validate_contract(contract)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        message = f"Input error: {exc}"
        if args.format == "json":
            # Machine-readable failures stay on stdout so a tool caller receives
            # exactly one JSON document even when the process exits non-zero.
            print(format_json_error(message))
        else:
            print(message, file=sys.stderr)
        return 2

    if args.format == "json":
        print(format_json(report))
    else:
        print(format_text(report))

    if report.verdict is Verdict.BLOCK:
        return 1
    if report.verdict is Verdict.REVIEW and args.warnings_as_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
