---
name: claim-foil
description: Stress-test a proposed analytical claim by generating a small set of materially distinct rival explanations, separating observed evidence from hypotheses, and naming the evidence that would discriminate among them before claim-contract validation.
---

# Claim Foil

## Purpose

Stress-test a proposed analytical claim before it is handed to `claim-contract`.

`claim-foil` generates a small set of **rival explanations** that could account for the same observed result, then identifies the evidence that would distinguish the proposed claim from those rivals. It is an adversarial reasoning aid, not a validator and not a truth detector.

The skill must preserve the repository's core boundary: **plausibility is not evidence**. A foil may be worth testing even when no current evidence supports it, but it must remain visibly labeled as a hypothesis until evidence is supplied.

`claim-foil` does not produce `READY`, `REVIEW`, or `BLOCK`. Those verdicts belong to `claim-contract`.

## Hard invariants

These are non-negotiable:

1. **Evidence conservation** — do not add facts that are not present in the supplied material. Every `OBSERVED` statement must be traceable to supplied evidence, with the narrowest available locator.
2. **Hypothesis labeling** — a plausible rival remains a `FOIL`; compatibility with the context is not evidence for it.
3. **Missing stays missing** — absent diagnostics, provenance, baselines, uncertainty, assignment checks, assumptions, or comparisons remain `UNKNOWN`.
4. **No negative-evidence inversion** — `none supplied` does not count as evidence against a foil unless the supplied material establishes that a relevant search or diagnostic was actually performed and found nothing material.
5. **No quota filling** — retain zero, one, two, or three foils according to usefulness. Never invent a third foil because the template has room for one.
6. **No verdict laundering** — neither a weak foil nor a failed discriminator can create a `READY`, `REVIEW`, or `BLOCK` result, and a mechanically `READY` contract cannot erase unresolved foil uncertainty.
7. **No lifecycle mutation by implication** — naming a rival explanation does not automatically set a contract check, populate an assumptions ledger, or change an assumption to `REVIEWED`, `CHALLENGED`, or `RETIRED`.

## When to use

Use before contract validation when a proposed claim could be materially weakened by a plausible alternative interpretation, especially for:

- causal claims;
- before/after comparisons;
- treatment/control comparisons;
- trend or time-series claims;
- subgroup or segmentation claims;
- qualitative magnitude claims;
- claims based on a metric whose definition, population, or measurement process may have shifted.

Skip it for purely mechanical declarations where no rival interpretation is decision-relevant.

Do not use it as an excuse to generate an unlimited list of generic caveats. Default to the **1-3 strongest materially distinct foils**.

## Inputs

Use only what is actually available:

- the proposed claim text;
- claim type, metric, population, and time window if known;
- the declared or observed evidence;
- relevant diagnostics, caveats, provenance, and source references;
- an existing `claim-contract` document if one already exists;
- an existing assumptions ledger if one is explicitly supplied.

Do not invent sample sizes, baselines, uncertainty, diagnostics, assignment mechanisms, identifying assumptions, missingness checks, composition checks, provenance, or assumption-review state.

## Evidence classes

Keep these categories explicit:

- `OBSERVED` — directly supported by the supplied evidence; include a locator when available.
- `FOIL` — a rival explanation or interpretation being proposed for stress-testing.
- `UNKNOWN` — evidence needed to evaluate a foil that has not been supplied.
- `DISCRIMINATOR` — a concrete observation, diagnostic, comparison, or design feature that would help distinguish the proposed claim from the foil.

A `FOIL` is not an `OBSERVED` fact. An `UNKNOWN` must not be silently filled with a plausible value.

### Source discipline

For `OBSERVED` statements:

- prefer an exact file/path, report field, table/figure, line range, query result, or user-supplied statement locator;
- preserve the supplied wording when a semantic rewrite could strengthen the evidence;
- distinguish a declared check from an independently verified check;
- distinguish `false` from missing and explicit `null` from absent where the source makes that distinction;
- do not cite a source for a stronger statement than it actually supports.

If no locator exists, say `[supplied context; locator unavailable]` rather than inventing one.

## Foil admission gate

A candidate foil must pass **all five** tests before it is retained:

1. **Compatible** — it is not contradicted by supplied `OBSERVED` evidence.
2. **Competitive** — if true, it could explain a material part of the same observed pattern or materially narrow the permissible claim.
3. **Distinct** — it is not merely a rewording or downstream consequence of another retained foil.
4. **Discriminable** — at least one concrete discriminator can be named from observable or inspectable evidence.
5. **Decision-relevant** — resolving it could change claim wording, contract completeness, a caveat, or the need for human review.

Reject a foil that is only a generic possibility, requires invented context to matter, or ends with a vague instruction such as “investigate further.”

When context is thin, it is acceptable to retain **no foil** and state that the supplied evidence is insufficient to generate a decision-relevant rival without speculation. That is not a claim endorsement.

## Workflow

1. State the proposed claim exactly as supplied. Do not soften, strengthen, or rewrite it.
2. Build a minimal evidence inventory of only the `OBSERVED` facts that bear on the claim, each with a locator when available.
3. Identify the claim's central burden without upgrading the claim type. A descriptive claim does not acquire a causal burden merely because causal foils are imaginable.
4. Generate candidate rival explanations, prioritizing those that could explain the same observed result through a materially different mechanism or interpretation.
5. Apply the foil admission gate. Collapse near-duplicates and discard generic filler.
6. Keep at most 3 retained foils unless the user explicitly asks for broader exploration.
7. For each retained foil, separate:
   - why it competes with the proposed claim;
   - supplied evidence that supports it, if any;
   - supplied evidence that weakens it, if any;
   - evidence that is still `UNKNOWN`;
   - the most useful `DISCRIMINATOR`;
   - what result would meaningfully favor the proposed interpretation versus the foil, when that distinction can be stated without inventing a threshold.
8. Rank foils by **decision relevance**, not rhetorical cleverness or novelty.
9. Identify any declaration in an existing contract that would be unsafe to mark complete until a discriminator is checked.
10. If an assumptions ledger is supplied, identify relevant assumption IDs only when the mapping is explicit. Do not create or change lifecycle status from the foil exercise alone.
11. Stop. Do not convert the foil exercise into a scientific verdict, a rewritten claim, a completed contract, an assumptions-ledger adjudication, or open-ended method search.

## Discriminator quality

A useful discriminator must be specific enough that another analyst can tell what evidence would bear on the foil.

Good discriminators:

- name the observable, diagnostic, comparison, or design feature to inspect;
- identify the relevant scope or groups when known;
- explain how the result would separate the proposed interpretation from the foil;
- avoid invented significance thresholds, effect-size cutoffs, or method requirements unless they were supplied or predeclared.

Weak discriminators include:

- “do more analysis”;
- “check for confounding”;
- “run robustness checks”;
- “collect more data”;
- “use a causal method.”

Those may be directions for future work, but they do not yet discriminate between hypotheses.

## Foil families

Use these only as prompts for search, not as a checklist that must be exhausted:

- **composition / selection** — the compared populations changed;
- **measurement / definition** — the metric, instrumentation, logging, or denominator changed;
- **time / environment** — seasonality, secular trend, concurrent events, or regression to the mean could explain the pattern;
- **assignment / exposure** — treatment receipt, contamination, or selection into treatment differs from the intended design;
- **missingness / censoring** — who is observed or retained changed;
- **model / specification** — the estimate depends materially on a modeling or functional-form choice;
- **multiplicity / selection of results** — the reported result may be one of many examined comparisons;
- **magnitude interpretation** — the numeric change may be real while the qualitative label overstates its substantive importance.

Do not present a foil from one of these families as applicable unless it is at least compatible with the supplied context. If the context is too thin, reject it rather than disguising a generic caveat as a case-specific foil.

## Output

Emit one compact packet:

```text
CLAIM FOIL

Proposed claim:
- ...

Observed evidence:
- OBSERVED — ... [locator]

Central burden:
- ...

Foils:
1. FOIL — ...
   Admission: compatible + competitive + distinct + discriminable + decision-relevant
   Why it competes: ...
   Evidence for: ... | none supplied
   Evidence against: ... | none supplied
   UNKNOWN: ...
   DISCRIMINATOR: ...
   Resolution signal: ... | cannot be stated from supplied context without inventing a threshold

Contract implications:
- ...

Assumption implications:
- ... | none from supplied material

Residual uncertainty:
- ...
```

If no materially useful foil passes the admission gate, say:

```text
Foils:
- None retained from the supplied context without speculation.
```

Do not translate that outcome into “the claim survives,” “no alternatives exist,” or scientific approval.

## Contract handoff

`claim-foil` is upstream of `claim-contract`:

```text
analysis + proposed claim
          ↓
      claim-foil
          ↓
rival explanations + discriminating evidence
          ↓
    claim-contract
          ↓
 READY / REVIEW / BLOCK on declared fields
```

The foil packet may reveal evidence that should remain missing or caveated in the contract, but it must not set a contract field to `true` merely because a discriminator was named.

If a discriminator is actually executed and produces evidence, that evidence can be added to the contract through the normal workflow and validated again.

### Assumptions-ledger handoff

The assumptions ledger is a separate sidecar review artifact. `claim-foil` may expose a premise that is worth recording there, but it does not create assumption truth or lifecycle state.

- A generated foil is not enough to create a `CHALLENGED` assumption.
- A named discriminator is not enough to create a `REVIEWED` assumption.
- If an existing ledger is supplied, preserve its stable IDs, bound contract/profile identity, and recorded status.
- If evidence produced by a discriminator later bears on an assumption, update the ledger through its explicit review/challenge workflow rather than rewriting the foil packet into ledger state.

See [`docs/ASSUMPTIONS_LEDGER.md`](../../docs/ASSUMPTIONS_LEDGER.md).

## Stop conditions

Stop the foil pass when any of the following is true:

- 1-3 decision-relevant, materially distinct foils have passed the admission gate;
- remaining candidates are duplicates, generic caveats, or require invented facts;
- no discriminator can be stated without method-shopping or speculation;
- the task is drifting into open-ended EDA, model selection, literature review, or redesign of the analysis.

A short packet with one strong foil is better than a long packet with three weak ones.

## Safety boundaries

- Do not treat a foil as refutation.
- Do not treat a plausible explanation as observed evidence.
- Do not claim the strongest foil is the true explanation.
- Do not infer missing diagnostics from domain conventions.
- Do not treat absence of supplied evidence as evidence against a foil.
- Do not rewrite a blocked claim into softer language and call it approved.
- Do not use a mechanically `READY` contract to dismiss unresolved foils.
- Do not use unresolved foils to claim the original assertion is false.
- Do not generate `READY`, `REVIEW`, or `BLOCK`; only `claim-contract` owns those verdicts.
- Do not auto-populate or mutate assumptions-ledger lifecycle state.
- Do not expand into open-ended EDA, model selection, or method recommendation unless the user explicitly asks for that separate work.

## Success looks like

- The proposed claim meets its strongest plausible rival interpretations before publication.
- Observed evidence remains distinct from generated hypotheses.
- Every retained foil passes the admission gate and names a concrete discriminator instead of ending as a vague caveat.
- Evidence locators make the packet auditable back to the supplied material.
- Near-duplicate and generic foils are rejected rather than padded into the output.
- Missing evidence remains missing.
- Contract fields and assumptions-ledger states are never upgraded by implication.
- The packet is small enough to use as a pre-validation gate.
- The downstream contract becomes more honest without making `claim-foil` look like a scientist or validator.
