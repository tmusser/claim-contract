# Claim DAG

The claim DAG is an **optional sidecar artifact** for making claim dependencies inspectable when an analytical story starts to depend on several subclaims, assumptions, or evidence items.

It exists to answer a narrow structural question:

> If this dependency gets shaky, which claims sit downstream of it?

It does **not** answer whether a claim is true, false, scientifically valid, publishable, or decision-worthy.

## Why a DAG

A single claim contract is intentionally local: one proposed claim, one declared evidence package, one deterministic verdict under a selected profile.

That is enough for many analyses. It becomes harder to reason about when a high-level statement depends on several intermediate assertions, for example:

```text
Ship the redesign
  requires -> redesign improves activation
                requires -> populations are comparable
                requires -> effect is material
                              requires -> uncertainty evidence exists
```

A flat checklist can hide two useful facts:

- one weak dependency may sit under several claims at once;
- a claim may look simple in prose while resting on a deep dependency chain.

The DAG makes those relationships visible without changing any source artifact.

## Artifact boundary

The v1 artifact is `claim_contract.claim_dag` and carries explicit safety fields:

```yaml
schema_version: "1.0"
type: claim_contract.claim_dag
scope_notice: >-
  Claim DAG records declared dependency structure and structural fragility
  signals. It is not scientific validation and does not prove any claim,
  assumption, or evidence item true or false.
scientific_validation: false
automatic_adjudication: false
mutates_source_artifacts: false
```

A DAG may point at claims, assumptions, or evidence already represented elsewhere, but it does not overwrite their status, lifecycle, verdict, or provenance.

The current `minimum-v0.1` validator does not consume claim DAGs.

## Nodes

A node has one of three kinds:

- `CLAIM` — a root claim or intermediate claim;
- `ASSUMPTION` — a premise the claim depends on;
- `EVIDENCE` — an evidence item or evidence requirement.

Each node also carries an `attention` annotation used only for review triage:

| State | Meaning |
| --- | --- |
| `NONE` | No fragility signal is recorded for this node. This does **not** mean verified, true, complete, or safe. |
| `WATCH` | Something about the node deserves explicit review before relying on downstream claims. |
| `CHALLENGED` | A material unresolved objection has been recorded. |
| `MISSING` | A dependency expected by the author is explicitly absent. |

`WATCH`, `CHALLENGED`, and `MISSING` require a reason. `refs` should point to the source material behind the annotation when available.

The DAG does not infer these states from prose and does not silently map source-artifact statuses into them. If a DAG mirrors an assumptions ledger or claim ledger, preserve the source semantics and record the mapping explicitly in the node note/references.

## Edges

Edges always point **from a claim to something the claim refers to**:

- `REQUIRES` — the author declares the target as a prerequisite for the source claim;
- `SUPPORTED_BY` — the target is relevant support for the source claim;
- `QUALIFIED_BY` — the target constrains or qualifies how the source claim should be interpreted.

Only `REQUIRES` edges propagate structural fragility in v1.

That choice is deliberate. A support or qualifier relationship may be important without being a declared prerequisite. Automatically treating every support edge as a single point of failure would make the graph look more certain about argument structure than the author actually declared.

Every edge source must be a `CLAIM` node. Nodes may still have many incoming edges, so one assumption or evidence item can expose several claims at once.

## Structural fragility

`claim-dag inspect` performs mechanical graph triage over `REQUIRES` paths.

A root claim is shown as `EXPOSED` when a required dependency reachable from that root has attention state:

- `WATCH`;
- `CHALLENGED`; or
- `MISSING`.

The inspection also reports:

- the path from the root claim to the flagged dependency;
- maximum required-dependency depth for each root;
- downstream claim blast radius for each flagged dependency;
- dependencies whose recorded fragility signal affects more than one downstream claim.

There is deliberately **no numeric fragility score**.

A score would collapse different semantics—missing evidence, an unresolved assumption, long dependency depth, and a shared dependency—into a precision-looking number whose interpretation would be arbitrary. V1 keeps the actual structural reasons visible.

`EXPOSED` is not a verdict. It means only that the author-declared required path reaches a node with a recorded attention signal.

## Rendering

Inspect a DAG in text:

```bash
claim-dag inspect examples/claim_dag/dag.yaml
```

Render Mermaid suitable for GitHub Markdown or any Mermaid-capable viewer:

```bash
claim-dag render examples/claim_dag/dag.yaml
```

The renderer uses:

- solid arrows for `REQUIRES`;
- dashed arrows for `SUPPORTED_BY` and `QUALIFIED_BY`;
- stronger outlines for `WATCH`, `CHALLENGED`, and `MISSING` nodes;
- a heavier outline for root claims with recorded required-path exposure.

The renderer is visual transport only. Styling does not add scientific meaning.

## Semantic validation

The published JSON Schema checks the artifact shape. The runtime loader additionally rejects:

- duplicate node IDs;
- unknown root IDs;
- roots that are not `CLAIM` nodes;
- edges that reference unknown nodes;
- edges whose source is not a `CLAIM` node;
- duplicate edges;
- self-edges;
- graph cycles.

A graph with a cycle is not a DAG and is rejected rather than silently rendered.

## Relationship to other artifacts

The artifacts remain separate:

```text
claim-foil
  rival explanations / discriminators
          ↓
claim-contract
  declared contract verdict
          ↓
optional assumptions ledger
  explicit premise lifecycle
          ↓
optional claim DAG
  dependency structure / blast radius / visual triage
```

The arrows above show a common workflow, not mandatory execution order. A DAG can be created whenever dependency structure becomes useful.

Important boundaries:

- a `BLOCK` contract does not automatically mark a DAG node `CHALLENGED`;
- a `CHALLENGED` assumptions-ledger entry does not automatically mutate a DAG;
- a DAG `WATCH` node does not mutate an assumptions ledger;
- a DAG cannot produce or reinterpret `READY`, `REVIEW`, or `BLOCK`;
- a mechanically unexposed DAG does not mean the claims are robust;
- a deep DAG does not mean the analysis is bad;
- a shallow DAG does not mean the analysis is good.

## Worked example

[`examples/claim_dag/`](../examples/claim_dag/) shows two high-level claims that share the same activation-effect dependency. That intermediate claim requires both a population-comparability assumption marked `WATCH` and an uncertainty evidence item marked `MISSING`.

The structural result is useful without overclaiming:

- both root claims are exposed through declared `REQUIRES` paths;
- the watched assumption has a multi-claim blast radius;
- the missing uncertainty item affects the material-effect branch;
- none of those facts proves the activation claim false.

Published schema: [`schemas/claim-dag-v1.schema.json`](../schemas/claim-dag-v1.schema.json).