# Bounded chart handoff

`claim-contract` can emit a versioned JSON handoff for downstream chart work:

```bash
claim-contract handoff chart contract.yaml > chart-handoff.json
```

The artifact type is `claim_contract.chart_handoff` with `schema_version: "1.0"`. Its published schema is [`schemas/chart-handoff-v1.schema.json`](../schemas/chart-handoff-v1.schema.json).

The handoff is intentionally conservative. It says what downstream chart work may inherit from the declared analytical contract; it does not choose or authorize a visualization.

## What is carried forward

The v1 envelope contains only:

- the exact proposed claim text;
- metric name and unit;
- declared population and time window;
- provenance source;
- declared caveats;
- the `claim-contract` validation verdict, profile, scope notice, `not_evaluated`, summary, and findings;
- the exact parsed-contract SHA-256 binding and contract/profile version metadata;
- source-tool and destination metadata.

Missing transferable values remain `null`. The exporter does not infer or manufacture them.

## What is deliberately absent

The handoff does **not** contain or recommend:

- chart type;
- Vega-Lite mark or encoding;
- aggregation or transformation choices;
- axis, scale, normalization, or truncation choices;
- color, layout, annotation, or title recommendations;
- a claim rewrite;
- scientific interpretation or approval.

The schema is closed-world (`additionalProperties: false`) at the envelope boundaries. Adding chart-design recommendations to a v1 handoff is therefore not silently compatible with this contract.

## Validation status is not stripped

A `REVIEW` or `BLOCK` contract may still be serialized so downstream tooling can see the unresolved status and findings. The CLI preserves validation-style exit semantics:

| Handoff status | Exit code |
| --- | ---: |
| `READY` | `0` |
| `REVIEW` | `0` |
| `REVIEW --warnings-as-errors` | `1` |
| `BLOCK` | `1` |
| malformed/unexportable input | `2` |

A nonzero exit does not suppress the JSON handoff when validation completed. This prevents a blocked claim from being laundered merely because it crossed a tool boundary.

## Contract identity

The handoff re-runs `claim-contract` on the supplied contract and embeds the same `parsed-contract-v1` SHA-256 binding used by validation reports.

Python callers can verify the in-memory relationship:

```python
from claim_contract import build_chart_handoff, load_contract

contract = load_contract("contract.yaml")
handoff = build_chart_handoff(contract)
assert handoff.matches_contract(contract)
```

The binding proves content identity only. It does not authenticate authorship, make the artifact tamper-proof, or prove the analysis is correct.

## Relationship to chart-contract

`chart-contract` currently audits a concrete chart/spec and can bind an explicit claim alongside the spec and data. This handoff does not construct that chart or invoke `chart-contract` automatically.

A downstream agent or workflow may carry the handoff's exact `claim.text` into chart-contract's claim input and use the declared unit, scope, provenance, caveats, and validation findings as constraints while authoring the visual. The resulting chart must still pass chart-contract's own independent audit.

In particular:

- do not soften or rewrite a `BLOCK`/`REVIEW` claim merely to make charting easier;
- do not drop population, time-window, provenance, or caveat context when it materially affects the visual claim;
- do not treat `claim-contract READY` as permission to choose a misleading chart;
- do not treat a chart-contract pass as scientific validation of the analytical claim.

The intended sequence is:

```text
analysis
  -> claim-contract contract
  -> bounded chart handoff
  -> chart authoring
  -> chart-contract audit
  -> human analytical judgment
```

Each stage keeps its own responsibility. The handoff only preserves the boundary between them.
