# Frozen minimum-v0.1 benchmark

This directory freezes the first benchmark artifact intended to provide evidence for ledger claim **CCL-002** without scoring the benchmark in the same change that defines its labels.

CCL-002 asks whether `minimum-v0.1` catches common evidence-to-language blocking violations while keeping false `BLOCK` verdicts low on bounded compliant claims. Its frozen judge contract requires at least 50 hand-labeled cases, labels fixed before validation, BLOCK recall of at least 80% for support, false-BLOCK rate of at most 10% for support, and traceability of every BLOCK to a documented implemented rule ID.

## Freeze contents

- `benchmark.yaml` — freeze metadata, class balance, covered families, and anti-circularity policy.
- `corpus.yaml` — 50 synthetic analytical claim/evidence cases represented as five full base contracts plus explicit dotted-path mutations.
- `labels.yaml` — 25 label-defined blocking violations and 25 nonblocking/review cases.
- `RUBRIC.md` — human labeling rubric independent of claim-contract verdicts and rule IDs.
- `evaluate.py` — deterministic scorer that materializes cases, runs the installed validator, emits case-level results and aggregate BLOCK metrics, and binds the result to exact corpus/label bytes plus the active profile-manifest identity.
- `schemas/benchmark-result-v1.schema.json` — strict machine-readable result schema.

## Why there are no results in this PR

The freeze is useful only if the labels precede the evidence intended to evaluate them. Repository CI therefore validates the benchmark's structure and evaluator mechanics **without running the frozen 50 cases through `minimum-v0.1`**.

After this freeze revision is merged, score that immutable revision in a separate evidence step:

```bash
python benchmarks/minimum-v0.1/evaluate.py \
  --output benchmarks/minimum-v0.1/results/minimum-v0.1.json
```

The result records SHA-256 identities for `corpus.yaml` and `labels.yaml` plus the semantic profile-manifest binding, so a later adjudicator can confirm exactly which frozen benchmark and ruleset produced the measurements.

## What gets measured

The evaluator reports:

- label-defined blocking-case count;
- label-defined nonblocking/review-case count;
- validator BLOCKs among labeled blocking cases;
- missed blocking cases;
- validator BLOCKs among labeled nonblocking/review cases;
- BLOCK recall;
- false-BLOCK rate;
- whether every emitted BLOCK rule ID exists in the selected machine-readable profile manifest;
- case-level label, verdict, and BLOCK rule IDs.

It deliberately does **not** turn those numbers into `SUPPORT_MET`, `REFUTE_MET`, or `INCONCLUSIVE`. A fresh adjudicator must apply the frozen CCL-002 judge contract separately.

## Corpus representation

The benchmark uses a compact materialization format rather than 50 near-duplicate YAML files. Each case names a complete base contract and optionally applies:

```yaml
set:
  evidence.checks.metric_definition_locked: false
delete:
  - evidence.provenance.source
```

`evaluate.py` deep-copies the base and applies those mutations deterministically. Repository tests materialize every frozen case without invoking the validator, which catches broken paths or malformed corpus structure while preserving the pre-score freeze.

## Label boundary

`labels.yaml` does not record expected validator verdicts or expected `CC###` rule IDs. A negative `blocking_violation` label may still be review-worthy. This is intentional because CCL-002's frozen metrics concern BLOCK recall and false-BLOCK rate, not exact three-way verdict agreement.

## Limitations

This is a synthetic, bounded benchmark built around recurring analytical failure modes. It is not an external representative sample of all data-science work, and strong performance cannot establish scientific validity, correctness of submitted declarations, or broad real-world generalization.
