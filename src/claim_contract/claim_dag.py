from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping
from pathlib import Path

import yaml


CLAIM_DAG_SCHEMA_VERSION = "1.0"
CLAIM_DAG_TYPE = "claim_contract.claim_dag"
CLAIM_DAG_SCOPE_NOTICE = (
    "Claim DAG records declared dependency structure and structural fragility signals. "
    "It is not scientific validation and does not prove any claim, assumption, or "
    "evidence item true or false."
)

NODE_KINDS = ("CLAIM", "ASSUMPTION", "EVIDENCE")
ATTENTION_STATES = ("NONE", "WATCH", "CHALLENGED", "MISSING")
EDGE_RELATIONS = ("REQUIRES", "SUPPORTED_BY", "QUALIFIED_BY")
FRAGILITY_ATTENTION_STATES = frozenset({"WATCH", "CHALLENGED", "MISSING"})


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object/mapping.")
    return value


def _require_nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value


def _require_string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_require_nonempty_string(item, f"{label}[{index}]"))
    return result


def load_claim_dag(path: str | Path) -> dict[str, object]:
    dag_path = Path(path)
    if not dag_path.exists():
        raise FileNotFoundError(f"Claim DAG file not found: {dag_path}")

    try:
        value = yaml.safe_load(dag_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Claim DAG is not valid YAML/JSON: {dag_path}: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError("Claim DAG root must be an object/mapping.")

    validate_claim_dag(value)
    return value


def validate_claim_dag(dag: Mapping[str, object]) -> None:
    if dag.get("schema_version") != CLAIM_DAG_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported claim DAG schema version: "
            f"{dag.get('schema_version')!r}."
        )
    if dag.get("type") != CLAIM_DAG_TYPE:
        raise ValueError(f"Expected claim DAG type {CLAIM_DAG_TYPE!r}.")
    if dag.get("scientific_validation") is not False:
        raise ValueError("Claim DAG scientific_validation must be false.")
    if dag.get("automatic_adjudication") is not False:
        raise ValueError("Claim DAG automatic_adjudication must be false.")
    if dag.get("mutates_source_artifacts") is not False:
        raise ValueError("Claim DAG mutates_source_artifacts must be false.")

    _require_nonempty_string(dag.get("title"), "title")
    roots = _require_string_list(dag.get("root_claim_ids"), "root_claim_ids")
    if not roots:
        raise ValueError("Claim DAG must declare at least one root_claim_id.")
    if len(roots) != len(set(roots)):
        raise ValueError("Claim DAG root_claim_ids must be unique.")

    raw_nodes = dag.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("Claim DAG nodes must be a non-empty list.")

    node_map: dict[str, Mapping[str, object]] = {}
    for index, raw_node in enumerate(raw_nodes):
        node = _require_mapping(raw_node, f"nodes[{index}]")
        node_id = _require_nonempty_string(node.get("id"), f"nodes[{index}].id")
        if node_id in node_map:
            raise ValueError(f"Duplicate claim DAG node id: {node_id}")

        kind = node.get("kind")
        if kind not in NODE_KINDS:
            raise ValueError(
                f"nodes[{index}].kind must be one of: {', '.join(NODE_KINDS)}."
            )
        _require_nonempty_string(node.get("label"), f"nodes[{index}].label")

        attention = _require_mapping(
            node.get("attention"), f"nodes[{index}].attention"
        )
        state = attention.get("state")
        if state not in ATTENTION_STATES:
            raise ValueError(
                f"nodes[{index}].attention.state must be one of: "
                + ", ".join(ATTENTION_STATES)
                + "."
            )
        reason = attention.get("reason")
        if state == "NONE":
            if reason is not None:
                raise ValueError(
                    f"nodes[{index}].attention.reason must be null when state is NONE."
                )
        else:
            _require_nonempty_string(reason, f"nodes[{index}].attention.reason")
        refs = _require_string_list(
            attention.get("refs"), f"nodes[{index}].attention.refs"
        )
        if len(refs) != len(set(refs)):
            raise ValueError(f"nodes[{index}].attention.refs must be unique.")

        note = node.get("note")
        if note is not None:
            _require_nonempty_string(note, f"nodes[{index}].note")

        node_map[node_id] = node

    for root_id in roots:
        node = node_map.get(root_id)
        if node is None:
            raise ValueError(f"Unknown root_claim_id: {root_id}")
        if node.get("kind") != "CLAIM":
            raise ValueError(f"Root node {root_id!r} must have kind CLAIM.")

    raw_edges = dag.get("edges")
    if not isinstance(raw_edges, list):
        raise ValueError("Claim DAG edges must be a list.")

    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_map}
    indegree = {node_id: 0 for node_id in node_map}
    seen_edges: set[tuple[str, str, str]] = set()

    for index, raw_edge in enumerate(raw_edges):
        edge = _require_mapping(raw_edge, f"edges[{index}]")
        source = _require_nonempty_string(edge.get("from"), f"edges[{index}].from")
        target = _require_nonempty_string(edge.get("to"), f"edges[{index}].to")
        relation = edge.get("relation")
        if relation not in EDGE_RELATIONS:
            raise ValueError(
                f"edges[{index}].relation must be one of: "
                + ", ".join(EDGE_RELATIONS)
                + "."
            )
        if source not in node_map:
            raise ValueError(f"edges[{index}] references unknown source node: {source}")
        if target not in node_map:
            raise ValueError(f"edges[{index}] references unknown target node: {target}")
        if source == target:
            raise ValueError(f"edges[{index}] cannot point a node to itself: {source}")
        if node_map[source].get("kind") != "CLAIM":
            raise ValueError(
                f"edges[{index}] source node {source!r} must have kind CLAIM."
            )
        signature = (source, target, str(relation))
        if signature in seen_edges:
            raise ValueError(
                f"Duplicate claim DAG edge: {source} -[{relation}]-> {target}"
            )
        seen_edges.add(signature)

        note = edge.get("note")
        if note is not None:
            _require_nonempty_string(note, f"edges[{index}].note")

        adjacency[source].append(target)
        indegree[target] += 1

    queue = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
    visited = 0
    while queue:
        node_id = queue.popleft()
        visited += 1
        for target in sorted(adjacency[node_id]):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)

    if visited != len(node_map):
        raise ValueError("Claim DAG contains a cycle; dependency graphs must be acyclic.")


def _node_map(dag: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    raw_nodes = dag["nodes"]
    assert isinstance(raw_nodes, list)
    result: dict[str, Mapping[str, object]] = {}
    for raw_node in raw_nodes:
        assert isinstance(raw_node, Mapping)
        node_id = str(raw_node["id"])
        result[node_id] = raw_node
    return result


def _required_adjacency(
    dag: Mapping[str, object], node_ids: set[str]
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    forward = {node_id: [] for node_id in node_ids}
    reverse = {node_id: [] for node_id in node_ids}
    raw_edges = dag["edges"]
    assert isinstance(raw_edges, list)
    for raw_edge in raw_edges:
        assert isinstance(raw_edge, Mapping)
        if raw_edge["relation"] != "REQUIRES":
            continue
        source = str(raw_edge["from"])
        target = str(raw_edge["to"])
        forward[source].append(target)
        reverse[target].append(source)
    for values in forward.values():
        values.sort()
    for values in reverse.values():
        values.sort()
    return forward, reverse


def _attention_state(node: Mapping[str, object]) -> str:
    attention = node["attention"]
    assert isinstance(attention, Mapping)
    return str(attention["state"])


def _downstream_claim_ids(
    dependency_id: str,
    reverse_required: Mapping[str, list[str]],
    node_map: Mapping[str, Mapping[str, object]],
) -> list[str]:
    seen: set[str] = set()
    stack = list(reverse_required[dependency_id])
    while stack:
        node_id = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        stack.extend(reverse_required[node_id])
    return sorted(
        node_id for node_id in seen if node_map[node_id].get("kind") == "CLAIM"
    )


def _max_required_depth(root_id: str, forward_required: Mapping[str, list[str]]) -> int:
    memo: dict[str, int] = {}

    def visit(node_id: str) -> int:
        if node_id in memo:
            return memo[node_id]
        children = forward_required[node_id]
        depth = 0 if not children else 1 + max(visit(child) for child in children)
        memo[node_id] = depth
        return depth

    return visit(root_id)


def analyze_claim_dag(dag: Mapping[str, object]) -> dict[str, object]:
    validate_claim_dag(dag)
    node_map = _node_map(dag)
    forward_required, reverse_required = _required_adjacency(dag, set(node_map))
    roots = list(dag["root_claim_ids"])
    signals: list[dict[str, object]] = []

    for root_id in roots:
        root_id = str(root_id)
        queue: deque[tuple[str, tuple[str, ...]]] = deque([(root_id, (root_id,))])
        visited: set[str] = set()
        while queue:
            node_id, path = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            node = node_map[node_id]
            attention = _attention_state(node)
            if attention in FRAGILITY_ATTENTION_STATES:
                signals.append(
                    {
                        "root_claim_id": root_id,
                        "dependency_id": node_id,
                        "attention": attention,
                        "path": list(path),
                        "downstream_claim_ids": _downstream_claim_ids(
                            node_id, reverse_required, node_map
                        ),
                    }
                )
            for child in forward_required[node_id]:
                queue.append((child, path + (child,)))

    signals.sort(
        key=lambda item: (
            str(item["root_claim_id"]),
            len(item["path"]),
            str(item["dependency_id"]),
        )
    )
    exposed_roots = sorted({str(item["root_claim_id"]) for item in signals})
    shared_fragile_dependencies = sorted(
        {
            str(item["dependency_id"])
            for item in signals
            if len(item["downstream_claim_ids"]) > 1
        }
    )

    return {
        "title": dag["title"],
        "root_claim_ids": roots,
        "exposed_root_claim_ids": exposed_roots,
        "root_required_depth": {
            str(root_id): _max_required_depth(str(root_id), forward_required)
            for root_id in roots
        },
        "signals": signals,
        "shared_fragile_dependency_ids": shared_fragile_dependencies,
        "scientific_validation": False,
        "automatic_adjudication": False,
        "scope_notice": CLAIM_DAG_SCOPE_NOTICE,
    }


def format_claim_dag_text(dag: Mapping[str, object]) -> str:
    analysis = analyze_claim_dag(dag)
    roots = [str(value) for value in analysis["root_claim_ids"]]
    exposed = set(str(value) for value in analysis["exposed_root_claim_ids"])
    depths = analysis["root_required_depth"]
    assert isinstance(depths, Mapping)
    signals = analysis["signals"]
    assert isinstance(signals, list)

    lines = [
        f"Claim DAG: {analysis['title']}",
        "Scientific validation: false",
        "Automatic adjudication: false",
        "Fragility score: none",
        "",
        "Root claims:",
    ]
    for root_id in roots:
        exposure = "EXPOSED" if root_id in exposed else "NO RECORDED EXPOSURE"
        lines.append(
            f"  {root_id}: {exposure}; required depth {int(depths[root_id])}"
        )

    lines.append("")
    lines.append("Structural fragility signals:")
    if not signals:
        lines.append("  none recorded on required dependency paths")
    else:
        for signal in signals:
            assert isinstance(signal, Mapping)
            path = " -> ".join(str(value) for value in signal["path"])
            downstream = ", ".join(
                str(value) for value in signal["downstream_claim_ids"]
            )
            if not downstream:
                downstream = "none"
            lines.extend(
                [
                    f"  {signal['root_claim_id']} -> {signal['dependency_id']} "
                    f"[{signal['attention']}]",
                    f"    path: {path}",
                    f"    downstream claim blast radius: {downstream}",
                ]
            )

    shared = analysis["shared_fragile_dependency_ids"]
    assert isinstance(shared, list)
    lines.append("")
    lines.append(
        "Shared fragile dependencies: " + (", ".join(shared) if shared else "none")
    )
    lines.append(
        "Boundary: exposure is mechanical graph triage only; it does not establish claim falsity or scientific weakness."
    )
    return "\n".join(lines)


def _escape_mermaid_label(value: object) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', "&quot;")
        .replace("\n", " ")
    )


def render_claim_dag_mermaid(dag: Mapping[str, object]) -> str:
    analysis = analyze_claim_dag(dag)
    node_map = _node_map(dag)
    ordered_node_ids = list(node_map)
    mermaid_ids = {node_id: f"n{index}" for index, node_id in enumerate(ordered_node_ids)}
    exposed_roots = set(str(value) for value in analysis["exposed_root_claim_ids"])

    lines = [
        "flowchart TD",
        "  %% Structural fragility triage only; not scientific validation.",
    ]

    for node_id in ordered_node_ids:
        node = node_map[node_id]
        label = _escape_mermaid_label(node["label"])
        kind = str(node["kind"])
        lines.append(f'  {mermaid_ids[node_id]}["{kind} · {label}"]')

    raw_edges = dag["edges"]
    assert isinstance(raw_edges, list)
    for raw_edge in raw_edges:
        assert isinstance(raw_edge, Mapping)
        source = mermaid_ids[str(raw_edge["from"])]
        target = mermaid_ids[str(raw_edge["to"])]
        relation = str(raw_edge["relation"])
        if relation == "REQUIRES":
            lines.append(f"  {source} -->|requires| {target}")
        elif relation == "SUPPORTED_BY":
            lines.append(f"  {source} -.->|supported by| {target}")
        else:
            lines.append(f"  {source} -.->|qualified by| {target}")

    lines.extend(
        [
            "  classDef watch stroke:#b45309,stroke-width:3px;",
            "  classDef challenged stroke:#b91c1c,stroke-width:3px;",
            "  classDef missing stroke:#6b21a8,stroke-width:3px,stroke-dasharray:5 3;",
            "  classDef exposed stroke:#374151,stroke-width:4px;",
        ]
    )

    for node_id in ordered_node_ids:
        state = _attention_state(node_map[node_id])
        if state == "WATCH":
            lines.append(f"  class {mermaid_ids[node_id]} watch;")
        elif state == "CHALLENGED":
            lines.append(f"  class {mermaid_ids[node_id]} challenged;")
        elif state == "MISSING":
            lines.append(f"  class {mermaid_ids[node_id]} missing;")
        if node_id in exposed_roots:
            lines.append(f"  class {mermaid_ids[node_id]} exposed;")

    return "\n".join(lines)
