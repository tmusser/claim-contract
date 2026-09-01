from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from .binding import (
    build_contract_binding,
    build_profile_manifest_binding,
    contract_binding_from_dict,
    profile_manifest_binding_from_dict,
)
from .contract_diff import ContractDiff, build_contract_diff
from .formatters import format_json, format_json_error, format_text
from .handoff import build_chart_handoff, handoff_exit_code
from .io import load_contract
from .ledger import (
    LEDGER_STATUSES,
    LedgerInspection,
    inspect_ledger,
    verify_pinned_provenance,
)
from .metadata import (
    REPORT_SCHEMA_VERSION,
    REPORT_TYPE,
    TOOL_NAME,
    TOOL_VERSION,
)
from .models import Verdict
from .profiles import ProfileManifest, get_profile_manifest
from .validator import validate_contract


DEFAULT_LEDGER_PATH = "claims/ledger.yaml"


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
    validate.add_argument(
        "contract",
        help="Path to the contract file, or - to read YAML/JSON from stdin.",
    )
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

    contract = subparsers.add_parser(
        "contract",
        help="Inspect differences between parsed analytical contracts.",
    )
    contract_commands = contract.add_subparsers(dest="contract_command", required=True)
    contract_diff = contract_commands.add_parser(
        "diff",
        help="Compare two parsed contracts and their validation verdicts.",
    )
    contract_diff.add_argument(
        "before",
        help="Earlier YAML/JSON contract path, or - to read it from stdin.",
    )
    contract_diff.add_argument(
        "after",
        help="Later YAML/JSON contract path, or - to read it from stdin.",
    )
    contract_diff_output = contract_diff.add_mutually_exclusive_group()
    contract_diff_output.add_argument(
        "--format",
        choices=("text", "json"),
        dest="format",
        help="Output format.",
    )
    contract_diff_output.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="Shortcut for --format json.",
    )
    contract_diff.set_defaults(format="text")

    handoff = subparsers.add_parser(
        "handoff",
        help="Emit bounded downstream handoff artifacts.",
    )
    handoff_commands = handoff.add_subparsers(dest="handoff_command", required=True)
    chart_handoff = handoff_commands.add_parser(
        "chart",
        help="Emit a bounded JSON claim context for chart-contract.",
    )
    chart_handoff.add_argument(
        "contract",
        help="Path to the YAML or JSON contract, or - to read from stdin.",
    )
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

    ledger_list = ledger_commands.add_parser(
        "list",
        help="List recorded ledger claims without adjudicating them.",
    )
    ledger_list.add_argument(
        "ledger",
        nargs="?",
        default=DEFAULT_LEDGER_PATH,
        help=f"Ledger path (default: {DEFAULT_LEDGER_PATH}).",
    )
    ledger_list.add_argument(
        "--status",
        help="Filter by recorded status: " + ", ".join(LEDGER_STATUSES) + ".",
    )
    ledger_list_output = ledger_list.add_mutually_exclusive_group()
    ledger_list_output.add_argument(
        "--format",
        choices=("text", "json"),
        dest="format",
        help="Output format.",
    )
    ledger_list_output.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="Shortcut for --format json.",
    )
    ledger_list.set_defaults(format="text")

    ledger_show = ledger_commands.add_parser(
        "show",
        help="Show one recorded ledger claim without adjudicating it.",
    )
    ledger_show.add_argument("claim_id", help="Recorded claim ID, for example CCL-002.")
    ledger_show.add_argument(
        "ledger",
        nargs="?",
        default=DEFAULT_LEDGER_PATH,
        help=f"Ledger path (default: {DEFAULT_LEDGER_PATH}).",
    )
    ledger_show_output = ledger_show.add_mutually_exclusive_group()
    ledger_show_output.add_argument(
        "--format",
        choices=("text", "json"),
        dest="format",
        help="Output format.",
    )
    ledger_show_output.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="Shortcut for --format json.",
    )
    ledger_show.set_defaults(format="text")

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
        help="Current YAML/JSON contract path, or - to read the contract from stdin.",
    )

    return parser


def _format_contract_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _format_contract_diff_text(diff: ContractDiff) -> str:
    lines = [
        f"Verdict: {diff.before_verdict} -> {diff.after_verdict}",
        f"Contract changed: {'true' if diff.changed else 'false'}",
        "Scientific validation: false",
        "Automatic interpretation: false",
        "",
    ]

    if not diff.changes:
        lines.append("Changed fields: none")
        return "\n".join(lines)

    lines.append("Changed fields:")
    for change in diff.changes:
        lines.append(f"  {change.path} [{change.change_type}]")
        before = _format_contract_value(change.before) if change.before_present else "<MISSING>"
        after = _format_contract_value(change.after) if change.after_present else "<MISSING>"
        lines.append(f"    - {before}")
        lines.append(f"    + {after}")
    return "\n".join(lines)


def _run_contract_diff(before_path: str, after_path: str, output_format: str) -> int:
    if before_path == "-" and after_path == "-":
        message = "Input error: only one side of contract diff may read from stdin."
        if output_format == "json":
            print(format_json_error(message))
        else:
            print(message, file=sys.stderr)
        return 2

    try:
        before = load_contract(before_path)
        after = load_contract(after_path)
        diff = build_contract_diff(before, after)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        message = f"Input error: {exc}"
        if output_format == "json":
            print(format_json_error(message))
        else:
            print(message, file=sys.stderr)
        return 2

    if output_format == "json":
        print(json.dumps(diff.to_dict(), indent=2, sort_keys=True))
    else:
        print(_format_contract_diff_text(diff))
    return 0


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


def _format_ledger_inspection_text(inspection: LedgerInspection) -> str:
    lines = [
        f"Ledger: {inspection.ledger_type} schema {inspection.ledger_schema_version}",
        f"Claims: {len(inspection.claims)}",
        "Automatic adjudication: false",
        f"Inspection: {inspection.mode}",
        "",
    ]

    for claim in inspection.claims:
        lines.extend(
            [
                f"{claim['id']} {claim['status']}",
                f"  Claim: {claim.get('claim', '')}",
                f"  Next adjudication: {claim.get('next_adjudication', '')}",
            ]
        )
        if inspection.mode == "show":
            judge_contract = claim.get("judge_contract")
            if isinstance(judge_contract, Mapping):
                lines.extend(
                    [
                        f"  Support if (recorded, not evaluated): {judge_contract.get('support_if', '')}",
                        f"  Refute if (recorded, not evaluated): {judge_contract.get('refute_if', '')}",
                        f"  Otherwise (recorded): {judge_contract.get('otherwise', '')}",
                    ]
                )
        lines.append("")

    return "\n".join(lines).rstrip()


def _run_ledger_inspection(
    path: str,
    output_format: str,
    *,
    status: str | None = None,
    claim_id: str | None = None,
) -> int:
    try:
        inspection = inspect_ledger(path, status=status, claim_id=claim_id)
        if output_format == "json":
            output = json.dumps(inspection.to_dict(), indent=2, sort_keys=True)
        else:
            output = _format_ledger_inspection_text(inspection)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    print(output)
    return 0


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

        serialized_profile_binding = contract_metadata.get("profile_manifest_binding")
        profile_binding = None
        profile_candidate = None
        if serialized_profile_binding is not None:
            if not isinstance(serialized_profile_binding, Mapping):
                raise ValueError(
                    "Report contract.profile_manifest_binding must be an object/mapping."
                )
            bound_profile = contract_metadata.get("profile")
            if not isinstance(bound_profile, str) or not bound_profile:
                raise ValueError(
                    "Report with profile_manifest_binding must declare contract.profile."
                )
            profile_binding = profile_manifest_binding_from_dict(
                serialized_profile_binding
            )
            manifest = get_profile_manifest(bound_profile)
            profile_candidate = build_profile_manifest_binding(manifest.to_dict())
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    contract_matches = binding == candidate
    profile_matches = (
        None
        if profile_binding is None
        else profile_binding == profile_candidate
    )
    matches = contract_matches and profile_matches is not False

    print(f"Binding: {'MATCH' if matches else 'MISMATCH'}")
    print(f"Contract SHA-256: {'MATCH' if contract_matches else 'MISMATCH'}")
    print(f"Saved SHA-256: {binding.contract_sha256}")
    print(f"Current SHA-256: {candidate.contract_sha256}")
    if profile_binding is None:
        print("Profile manifest SHA-256: UNBOUND")
    else:
        print(
            "Profile manifest SHA-256: "
            f"{'MATCH' if profile_matches else 'MISMATCH'}"
        )
        print(
            "Saved profile manifest SHA-256: "
            f"{profile_binding.profile_manifest_sha256}"
        )
        print(
            "Current profile manifest SHA-256: "
            f"{profile_candidate.profile_manifest_sha256}"
        )
    if "version" in contract_metadata:
        print(f"Bound contract version: {contract_metadata['version']}")
    if "profile" in contract_metadata:
        print(f"Bound profile: {contract_metadata['profile']}")
    return 0 if matches else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "contract":
        if args.contract_command == "diff":
            return _run_contract_diff(args.before, args.after, args.format)
        raise AssertionError(f"Unhandled contract command: {args.contract_command}")
    if args.command == "handoff":
        return _run_chart_handoff(args.contract, args.warnings_as_errors)
    if args.command == "profile":
        return _run_profile_show(args.profile, args.format)
    if args.command == "ledger":
        if args.ledger_command == "verify":
            return _run_ledger_verify(args.ledger)
        if args.ledger_command == "list":
            return _run_ledger_inspection(
                args.ledger,
                args.format,
                status=args.status,
            )
        if args.ledger_command == "show":
            return _run_ledger_inspection(
                args.ledger,
                args.format,
                claim_id=args.claim_id,
            )
        raise AssertionError(f"Unhandled ledger command: {args.ledger_command}")
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
