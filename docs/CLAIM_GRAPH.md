# Claim graph pruning

`claims/graph.yaml` is an optional relevance sidecar for the repository claim ledger.
It exists to answer one narrow question mechanically:

> Does each active claim have a declared relevance path to at least one named root claim?

This is **not** semantic claim ranking and it is not automatic retirement. The graph does not
try to decide whether a claim is true, useful, redundant, scientifically valid, or safe to
delete.

## Why a sidecar

The claim ledger freezes judgeable claims, evidence thresholds, provenance, and status.
Those semantics should not be overloaded with a mutable product/research relevance graph.
Keeping the graph separate means:

- claim IDs and ledger history remain unchanged;
- relevance structure can evolve without rewriting claim provenance;
- graph inspection cannot silently change `OPEN`, `SUPPORT_MET`, `REFUTE_MET`,
  `INCONCLUSIVE`, or `RETIRED`;
- a graph flag is visibly weaker than an adjudication.

## Graph contract

The v1 graph has two primitives:

- `roots` — active claims explicitly retained as top-level decision-relevant claims;
- `edges` — directed relevance edges from a narrower claim to the claim it contributes to.

Example:

```yaml
schema_version: "1.0"
type: claim_contract.claim_graph
scope_notice: "Claim-graph edges declare relevance only. Connectivity does not establish truth, support, entailment, scientific validity, or priority. A prune candidate is an active claim with no declared relevance path to a root; it is not automatically safe to delete or retire."
roots:
  - CCL-003
edges:
  - from: CCL-004
    to: CCL-003
    rationale: "CCL-004 tests a narrower mechanism that informs the root claim."
```

An edge means only that the source claim has been explicitly declared relevant to the target.
It does **not** mean logical implication, empirical support, causal identification, or truth.
The rationale is required so the relationship remains inspectable.

## Pruning classifications

The analyzer emits one classification per ledger claim:

- `ROOT` — the active claim is explicitly named as a graph root;
- `CONNECTED` — the active claim has a directed path to a root;
- `PRUNE_CANDIDATE` — the active claim has no directed path to any root;
- `RETIRED` — the ledger already records the claim as retired, so it is excluded from active
  pruning candidates.

`PRUNE_CANDIDATE` is deliberately cautious wording. It means "structurally disconnected from
the declared roots," not "bad claim" or "delete this."

## Fail-closed graph hygiene

The analyzer rejects malformed topology rather than guessing:

- unknown claim IDs in roots or edges;
- retired claims used as roots;
- self-edges;
- duplicate edges;
- relevance cycles.

Paths through retired claims do not count. A retired claim cannot be used as a bridge to make
an otherwise disconnected active claim look relevant.

The analyzer does not infer edges from similar wording, shared evidence, `supersedes`, file
references, or model judgment. Missing relevance remains missing.

## CLI

The pruning helper is intentionally read-only:

```bash
claim-contract graph prune
claim-contract graph prune claims/ledger.yaml --graph claims/graph.yaml
claim-contract graph prune --json
```

By default, prune candidates are reported but the process exits `0`. For a CI or agent gate,
opt into a nonzero exit code:

```bash
claim-contract graph prune --fail-on-candidate
```

Exit behavior:

- `0` — graph inspection completed; candidates may still be present unless
  `--fail-on-candidate` was requested;
- `1` — `--fail-on-candidate` was requested and at least one candidate was found;
- `2` — graph or ledger input is malformed or missing.

The JSON report includes `scientific_validation: false`, `automatic_retirement: false`, and
`mutates_ledger: false` so agents cannot reasonably reinterpret pruning as adjudication.

## Live graph

The repository currently declares `CCL-001`, `CCL-002`, and `CCL-003` as independent roots.
That is intentionally conservative: the current ledger records three separate top-level
research/product claims and does not contain evidence for a hierarchy among them.

Future claims should either be declared as roots or receive an explicit relevance path to a
root. If neither is justified, the analyzer will surface them as prune candidates for human
review.


Compatibility note: `claim-contract-graph` remains available as a backwards-compatible
executable, but new documentation uses the canonical `claim-contract graph ...` command
surface.
