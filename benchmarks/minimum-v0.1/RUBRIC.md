# minimum-v0.1 benchmark labeling rubric

This rubric defines the frozen human labels used by the `minimum-v0.1` benchmark targeted at ledger claim `CCL-002`.

The labels are intentionally **not** `READY`, `REVIEW`, or `BLOCK`, and they do not name expected claim-contract rule IDs. The benchmark asks a narrower question: does `minimum-v0.1` issue a `BLOCK` when the independently defined case contains a minimum evidence-to-language mismatch that should stop the claim as written?

## Label

Each case has one boolean label:

- `blocking_violation: true` — the declared claim/evidence pair contains an explicit mismatch or omission severe enough that a narrow pre-publication integrity gate should stop the claim as written before publication or automated downstream use.
- `blocking_violation: false` — the pair does not contain a label-defined blocking mismatch. It may still deserve qualified human review, caveats, or additional analysis.

A `false` label therefore does **not** mean “scientifically valid,” “READY,” or “safe to publish.” It means only that the benchmark rubric does not classify the case as a blocking evidence-to-language failure.

## Blocking criteria

Label `true` when the supplied declarations make the proposed language materially uninterpretable or materially stronger than the declared evidence in one of these bounded ways:

1. **Required analytical scope is absent or invalid.** The population, metric definition, provenance source, sample size, claim type, or another indispensable declaration is missing or unusable.
2. **A comparison is not identified.** A comparison claim omits a baseline/comparison group or makes a relative statement without the baseline needed to interpret that relative change.
3. **Magnitude language has no numerical anchor.** Words such as “substantial,” “material,” or “small” are used without a numeric estimate and declared scale.
4. **Causal language exceeds the declared design.** Attribution or intervention-effect language is paired with a design that does not support causal attribution at the minimum-contract level.
5. **A declared causal design omits a design-integrity prerequisite.** Randomized evidence lacks assignment validation, or quasi-experimental evidence lacks documented identifying assumptions.

## Nonblocking / review criteria

Label `false` when the case is interpretable at the minimum evidence-to-language level but still reasonably calls for review. Examples include:

- uncertainty is absent from an otherwise interpretable comparison;
- multiple-comparison risk was not assessed or handled;
- an observational before/after comparison lacks a composition-stability assessment;
- an observational comparison lacks an explicit non-causal caveat while still using non-causal claim language;
- a metric definition is declared but not locked;
- missingness was not assessed;
- an otherwise eligible randomized or quasi-experimental causal claim still requires qualified human review.

These are deliberately included among negative cases because `CCL-002` measures **BLOCK recall** and **false-BLOCK rate**, not exact three-way verdict agreement.

## Independence rules

To reduce circular labeling:

- labels must not contain expected `READY`, `REVIEW`, or `BLOCK` verdicts;
- labels must not contain expected `CC###` rule IDs;
- rationales should describe the analytical mismatch in ordinary analytical language rather than restating validator implementation details;
- changing validator behavior after the freeze does not change labels;
- changing a label after the first benchmark score requires a new benchmark version rather than silently editing v1.0.

## What the benchmark cannot establish

The corpus is synthetic and intentionally bounded around common evidence-to-language failure modes. It does not establish that the submitted declarations are true, that the underlying analyses are correct, that the rules generalize to every analytical domain, or that a low false-BLOCK rate implies a low false-REVIEW rate.

The first benchmark score should be produced only after the freeze revision is merged. The evaluator reports measurements and case-level outputs; it does not adjudicate `CCL-002` automatically.
