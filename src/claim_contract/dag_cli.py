from __future__ import annotations

import argparse
import sys

from .claim_dag import format_claim_dag_text, load_claim_dag, render_claim_dag_mermaid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claim-dag",
        description=(
            "Inspect or render an optional claim dependency DAG without scientific "
            "adjudication."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect = subparsers.add_parser(
        "inspect",
        help="Inspect structural fragility signals on declared REQUIRES paths.",
    )
    inspect.add_argument("dag", help="Path to a claim DAG YAML/JSON file.")

    render = subparsers.add_parser(
        "render",
        help="Render a claim DAG as Mermaid source.",
    )
    render.add_argument("dag", help="Path to a claim DAG YAML/JSON file.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        dag = load_claim_dag(args.dag)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    if args.command == "inspect":
        print(format_claim_dag_text(dag))
        return 0
    if args.command == "render":
        print(render_claim_dag_mermaid(dag))
        return 0
    raise AssertionError(f"Unhandled claim DAG command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
