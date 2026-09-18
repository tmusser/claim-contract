# Claim DAG worked example

This fixture demonstrates the optional `claim_contract.claim_dag` sidecar against the existing onboarding-conversion example.

It is intentionally **not** another validator fixture and does not change the onboarding contract's deterministic verdict.

## Shape

Two synthetic root claims share the same intermediate dependency:

```text
claim_ship_redesign
        \
         requires -> claim_redesign_improves_activation
        /              |                     |
claim_reuse_result     | requires            | requires
                       v                     v
          assumption_population       claim_effect_material
          _comparable [WATCH]                   |
                                                | requires
                                                v
                                   evidence_uncertainty [MISSING]
```

The source contract records:

- an observational before/after design;
- `composition_stability_assessed: false`;
- `uncertainty: null`;
- a relative estimate of `0.08` with baseline `0.25`.

The DAG does not upgrade or reinterpret those declarations. It uses them only to make two explicit review-triage annotations visible:

- population comparability is `WATCH` because composition stability was not assessed;
- uncertainty evidence is `MISSING` because the source contract explicitly records `uncertainty: null`.

`claim_effect_material` is also marked `WATCH` because substantive importance is a distinct interpretive burden from whether a numeric effect exists.

## Inspect

```bash
claim-dag inspect examples/claim_dag/dag.yaml
```

Expected structural result:

- both root claims are `EXPOSED` through declared `REQUIRES` paths;
- the population-comparability node has a multi-claim blast radius;
- the missing uncertainty evidence sits one level deeper under the materiality subclaim;
- there is no numeric fragility score.

`EXPOSED` means only that a required path reaches a node with `WATCH`, `CHALLENGED`, or `MISSING` attention. It does not mean the root claim is false or scientifically invalid.

## Render

```bash
claim-dag render examples/claim_dag/dag.yaml
```

The command emits Mermaid source. GitHub can render that source inside a Mermaid code block.

The rendered graph uses solid `REQUIRES` edges and dashed support/qualification edges. Attention styling is visual triage only.

See [`docs/CLAIM_DAG.md`](../../docs/CLAIM_DAG.md) for the artifact and propagation semantics.