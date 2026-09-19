from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .ledger import inspect_ledger

GRAPH_TYPE = "claim_contract.claim_graph"
GRAPH_SCHEMA_VERSION = "1.0"
PRUNE_REPORT_TYPE = "claim_contract.claim_graph_prune_report"
PRUNE_REPORT_SCHEMA_VERSION = "1.0"
DEFAULT_LEDGER_PATH = "claims/ledger.yaml"
DEFAULT_GRAPH_PATH = "claims/graph.yaml"

GRAPH_SCOPE_NOTICE = (
    "Claim-graph edges declare relevance only. Connectivity does not establish truth, "
    "support, entailment, scientific validity, or priority. A prune candidate is an active "
    "claim with no declared relevance path to a root; it is not automatically safe to "
    "delete or retire."
)

PRUNE_NOTICE = (
    "Pruning is read-only structural inspection. It does not adjudicate claims, infer "
    "semantic redundancy, change ledger status, or mutate either input file."
)

ROOT = "ROOT"
CONNECTED = "CONNECTED"
PRUNE_CANDIDATE = "PRUNE_CANDIDATE"
RETIRED = "RETIRED"


@dataclass(frozen=True)
class ClaimGraphFinding:
    claim_id: str
    status: str
    classification: str
    structurally_extraneous: bool
    path_to_root: tuple[str, ...] | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "status": self.status,
            "classification": self.classification,
            "structurally_extraneous": self.structurally_extraneous,
            "path_to_root": list(self.path_to_root) if self.path_to_root is not None else None,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ClaimGraphPruneReport:
    ledger_schema_version: str
    roots: tuple[str, ...]
    edge_count: int
    findings: tuple[ClaimGraphFinding, ...]

    @property
    def prune_candidates(self) -> tuple[ClaimGraphFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.classification == PRUNE_CANDIDATE
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PRUNE_REPORT_SCHEMA_VERSION,
            "type": PRUNE_REPORT_TYPE,
            "scientific_validation": False,
            "automatic_retirement": False,
            "mutates_ledger": False,
            "notice": PRUNE_NOTICE,
            "ledger": {
                "schema_version": self.ledger_schema_version,
                "type": "claim_contract.claim_ledger",
            },
            "graph": {
                "schema_version": GRAPH_SCHEMA_VERSION,
                "type": GRAPH_TYPE,
                "scope_notice": GRAPH_SCOPE_NOTICE,
                "roots": list(self.roots),
                "edge_count": self.edge_count,
            },
            "counts": {
                "claims": len(self.findings),
                "roots": sum(f.classification == ROOT for f in self.findings),
                "connected": sum(f.classification == CONNECTED for f in self.findings),
                "prune_candidates": len(self.prune_candidates),
                "retired": sum(f.classification == RETIRED for f in self.findings),
            },
            "claims": [finding.to_dict() for finding in self.findings],
        }


def _load_graph(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Claim graph file not found: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Claim graph root must be an object/mapping.")
    if value.get("schema_version") != GRAPH_SCHEMA_VERSION:
        raise ValueError(
            f"Claim graph schema_version must be {GRAPH_SCHEMA_VERSION!r}."
        )
    if value.get("type") != GRAPH_TYPE:
        raise ValueError(f"Claim graph type must be {GRAPH_TYPE!r}.")
    if value.get("scope_notice") != GRAPH_SCOPE_NOTICE:
        raise ValueError("Claim graph scope_notice does not match the v1 contract.")
    roots = value.get("roots")
    edges = value.get("edges")
    if not isinstance(roots, list) or not roots:
        raise ValueError("Claim graph roots must be a non-empty list.")
    if not all(isinstance(root, str) and root for root in roots):
        raise ValueError("Claim graph roots must be non-empty claim IDs.")
    if len(set(roots)) != len(roots):
        raise ValueError("Claim graph roots must be unique.")
    if not isinstance(edges, list):
        raise ValueError("Claim graph edges must be a list.")
    return value


def _normalize_edges(
    raw_edges: list[Any],
    *,
    claim_ids: set[str],
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, dict):
            raise ValueError(f"Claim graph edge {index} must be an object/mapping.")
        if set(edge) != {"from", "to", "rationale"}:
            raise ValueError(
                f"Claim graph edge {index} must contain exactly from, to, and rationale."
            )
        source = edge.get("from")
        target = edge.get("to")
        rationale = edge.get("rationale")
        if not isinstance(source, str) or not source:
            raise ValueError(f"Claim graph edge {index} has an invalid from claim ID.")
        if not isinstance(target, str) or not target:
            raise ValueError(f"Claim graph edge {index} has an invalid to claim ID.")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"Claim graph edge {index} must include a rationale.")
        if source not in claim_ids or target not in claim_ids:
            unknown = sorted({source, target} - claim_ids)
            raise ValueError(
                "Claim graph references unknown claim ID(s): " + ", ".join(unknown)
            )
        if source == target:
            raise ValueError(f"Claim graph cannot contain self-edge {source} -> {target}.")
        pair = (source, target)
        if pair in seen:
            raise ValueError(f"Claim graph contains duplicate edge {source} -> {target}.")
        seen.add(pair)
        normalized.append(
            {"from": source, "to": target, "rationale": rationale.strip()}
        )
    return normalized


def _assert_acyclic(claim_ids: set[str], edges: list[dict[str, str]]) -> None:
    adjacency: dict[str, list[str]] = {claim_id: [] for claim_id in claim_ids}
    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])
    for targets in adjacency.values():
        targets.sort()

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visiting:
            start = stack.index(node)
            cycle = stack[start:] + [node]
            raise ValueError("Claim graph contains a relevance cycle: " + " -> ".join(cycle))
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for target in adjacency[node]:
            visit(target, stack)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for claim_id in sorted(claim_ids):
        visit(claim_id, [])


def _path_to_root(
    claim_id: str,
    *,
    roots: set[str],
    adjacency: dict[str, tuple[str, ...]],
    active_ids: set[str],
) -> tuple[str, ...] | None:
    if claim_id in roots:
        return (claim_id,)

    queue: deque[tuple[str, tuple[str, ...]]] = deque([(claim_id, (claim_id,))])
    seen = {claim_id}
    while queue:
        current, path = queue.popleft()
        for target in adjacency.get(current, ()):  # deterministic sorted targets
            if target not in active_ids or target in seen:
                continue
            candidate_path = path + (target,)
            if target in roots:
                return candidate_path
            seen.add(target)
            queue.append((target, candidate_path))
    return None


def analyze_claim_graph(
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    graph_path: str | Path = DEFAULT_GRAPH_PATH,
) -> ClaimGraphPruneReport:
    inspection = inspect_ledger(ledger_path)
    claims = [deepcopy(claim) for claim in inspection.claims]
    claims_by_id = {str(claim["id"]): claim for claim in claims}
    claim_ids = set(claims_by_id)

    graph = _load_graph(Path(graph_path))
    roots = tuple(graph["roots"])
    unknown_roots = sorted(set(roots) - claim_ids)
    if unknown_roots:
        raise ValueError(
            "Claim graph roots reference unknown claim ID(s): " + ", ".join(unknown_roots)
        )

    retired_ids = {
        claim_id
        for claim_id, claim in claims_by_id.items()
        if claim.get("status") == "RETIRED"
    }
    retired_roots = sorted(set(roots) & retired_ids)
    if retired_roots:
        raise ValueError(
            "Retired claims cannot be graph roots: " + ", ".join(retired_roots)
        )

    edges = _normalize_edges(graph["edges"], claim_ids=claim_ids)
    _assert_acyclic(claim_ids, edges)

    adjacency_lists: dict[str, list[str]] = {claim_id: [] for claim_id in claim_ids}
    for edge in edges:
        adjacency_lists[edge["from"]].append(edge["to"])
    adjacency = {
        claim_id: tuple(sorted(targets))
        for claim_id, targets in adjacency_lists.items()
    }

    active_ids = claim_ids - retired_ids
    root_set = set(roots)
    findings: list[ClaimGraphFinding] = []
    for claim_id in sorted(claim_ids):
        claim = claims_by_id[claim_id]
        status = str(claim["status"])
        if claim_id in retired_ids:
            findings.append(
                ClaimGraphFinding(
                    claim_id=claim_id,
                    status=status,
                    classification=RETIRED,
                    structurally_extraneous=False,
                    path_to_root=None,
                    reason=(
                        "Recorded status is RETIRED, so the claim is excluded from active "
                        "graph-pruning candidates."
                    ),
                )
            )
            continue

        path = _path_to_root(
            claim_id,
            roots=root_set,
            adjacency=adjacency,
            active_ids=active_ids,
        )
        if claim_id in root_set:
            classification = ROOT
            reason = "Claim is an explicitly declared graph root."
        elif path is not None:
            classification = CONNECTED
            reason = "Active claim has a declared relevance path to a graph root."
        else:
            classification = PRUNE_CANDIDATE
            reason = (
                "Active claim has no declared relevance path to any graph root. This is a "
                "structural flag only, not a judgment that the claim is false or disposable."
            )

        findings.append(
            ClaimGraphFinding(
                claim_id=claim_id,
                status=status,
                classification=classification,
                structurally_extraneous=classification == PRUNE_CANDIDATE,
                path_to_root=path,
                reason=reason,
            )
        )

    return ClaimGraphPruneReport(
        ledger_schema_version=inspection.ledger_schema_version,
        roots=roots,
        edge_count=len(edges),
        findings=tuple(findings),
    )


def _format_text(report: ClaimGraphPruneReport) -> str:
    lines = [
        f"Claim graph: {GRAPH_TYPE} schema {GRAPH_SCHEMA_VERSION}",
        f"Roots: {', '.join(report.roots)}",
        f"Prune candidates: {len(report.prune_candidates)}",
        "Automatic retirement: false",
        "Scientific validation: false",
        "",
    ]
    for finding in report.findings:
        lines.append(f"{finding.classification} {finding.claim_id} [{finding.status}]")
        if finding.path_to_root is not None:
            lines.append("  Path to root: " + " -> ".join(finding.path_to_root))
        lines.append(f"  {finding.reason}")
    return "\n".join(lines)


def _configure_prune_parser(prune: argparse.ArgumentParser) -> None:
    prune.add_argument(
        "ledger",
        nargs="?",
        default=DEFAULT_LEDGER_PATH,
        help=f"Ledger path (default: {DEFAULT_LEDGER_PATH}).",
    )
    prune.add_argument(
        "--graph",
        default=DEFAULT_GRAPH_PATH,
        help=f"Claim graph path (default: {DEFAULT_GRAPH_PATH}).",
    )
    prune.add_argument("--json", action="store_true", help="Emit JSON output.")
    prune.add_argument(
        "--fail-on-candidate",
        action="store_true",
        help="Exit 1 when one or more prune candidates are present.",
    )


def add_graph_subparser(subparsers: argparse._SubParsersAction) -> None:
    graph = subparsers.add_parser(
        "graph",
        help="Inspect structural relevance among repository claims.",
    )
    graph_commands = graph.add_subparsers(dest="graph_command", required=True)
    prune = graph_commands.add_parser(
        "prune",
        help="Flag active claims with no path to a declared root.",
    )
    _configure_prune_parser(prune)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claim-contract-graph",
        description="Flag structurally disconnected claims without adjudicating them.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prune = subparsers.add_parser(
        "prune",
        help="Inspect a claim graph and flag active claims with no path to a declared root.",
    )
    _configure_prune_parser(prune)
    return parser


def run_prune_command(args: argparse.Namespace) -> int:
    try:
        report = analyze_claim_graph(args.ledger, args.graph)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(_format_text(report))

    if args.fail_on_candidate and report.prune_candidates:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "prune":
        raise AssertionError(f"Unhandled graph command: {args.command}")
    return run_prune_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
