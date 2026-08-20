from __future__ import annotations

import argparse
import sys

from .formatters import format_json, format_json_error, format_text
from .io import load_contract
from .ledger import verify_pinned_provenance
from .metadata import TOOL_NAME, TOOL_VERSION
from .models import Verdict
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

    return parser


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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ledger":
        return _run_ledger_verify(args.ledger)

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
