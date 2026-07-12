from __future__ import annotations

import argparse
import sys

from .formatters import format_json, format_text
from .io import load_contract
from .models import Verdict
from .validator import validate_contract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claim-contract",
        description="Validate a declared minimum contract for an analytical claim.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a YAML or JSON contract.")
    validate.add_argument("contract", help="Path to the contract file.")
    validate.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    validate.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Exit 1 for REVIEW as well as BLOCK.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        contract = load_contract(args.contract)
        report = validate_contract(contract)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
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
