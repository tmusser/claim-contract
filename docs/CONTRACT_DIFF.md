# Contract diff

`claim-contract contract diff` compares two parsed analytical contracts and reports the exact declared fields that changed together with the `READY | REVIEW | BLOCK` verdict transition.

```bash
claim-contract contract diff before.yaml after.yaml
claim-contract contract diff before.yaml after.yaml --json
```

The command is an inspection surface. A successful comparison exits `0` even if either contract validates as `BLOCK`; malformed or unreadable input exits `2`.

## What is compared

The diff runs after YAML/JSON parsing, so source formatting and mapping key order are not changes. Nested mapping fields are reported using dotted paths such as `claim.text` or `evidence.checks.composition_stability_assessed`.

Lists are treated as one declared field. If a caveat list changes, the diff reports the before/after list rather than attempting to infer item identity or semantic equivalence.

Missing and explicit `null` are distinct states. Machine-readable changes therefore carry both value fields and `before_present` / `after_present` flags.

Representative text output:

```text
Verdict: BLOCK -> READY
Contract changed: true
Scientific validation: false
Automatic interpretation: false

Changed fields:
  claim.text [changed]
    - "The redesign improved activation by 8%."
    + "Activation was 8% higher after the redesign."
  evidence.uncertainty [changed]
    - null
    + {"level":0.95,"lower":0.03,"method":"bootstrap","upper":0.12}
```

## Machine-readable output

`--json` emits `claim_contract.contract_diff` schema `1.0`, published at [`schemas/contract-diff-v1.schema.json`](../schemas/contract-diff-v1.schema.json).

The envelope includes:

- the before and after verdicts and whether the verdict changed;
- whether parsed contract content changed;
- a deterministic path-sorted list of `added`, `removed`, and `changed` fields;
- presence flags so missing is not collapsed into explicit `null`;
- `scientific_validation: false`, `automatic_interpretation: false`, a fixed scope notice, and explicit `not_evaluated` boundaries.

## Boundary

The command does **not**:

- decide whether a revision is scientifically or statistically appropriate;
- explain causally why the verdict changed;
- label edits as safe, unsafe, breaking, or sufficient;
- recommend claim wording;
- prove that new declarations are true;
- detect whether someone edited fields merely to make a contract mechanically green.

A `BLOCK -> READY` transition means only that the later submitted contract satisfied the implemented rules that blocked or reviewed the earlier declaration. The diff preserves the receipts; human analytical judgment still has to interpret them.

## stdin

Either side may use `-` as the contract source:

```bash
cat revised.yaml | claim-contract contract diff original.yaml -
```

Both sides cannot read from stdin in the same invocation.
