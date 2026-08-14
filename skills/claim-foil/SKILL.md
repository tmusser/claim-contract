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
- an existing `claim-contract` document if one already exists.

Do not invent sample sizes, baselines, uncertainty, diagnostics, assignment mechanisms, identifying assumptions, missingness checks, composition checks, or provenance.

## Evidence classes

Keep these categories explicit:

- `OBSERVED` — directly supported by the supplied evidence; include a locator when available.
- `FOIL` — a rival explanation or interpretation being proposed for stress-testing.
- `UNKNOWN` — evidence needed to evaluate a foil that has not been supplied.
- `DISCRIMINATOR` — a concrete observation, diagnostic, comparison, or design feature that would help distinguish the proposed claim from the foil.

A `FOIL` is not an `OBSERVED` fact. An `UNKNOWN` must not be silently filled with a plausible value.

## Workflow

1. State the proposed claim exactly as supplied. Do not soften, strengthen, or rewrite it.
2. Extract the smallest set of `OBSERVED` facts that actually bear on the claim.
3. Identify the claim's central explanatory burden: what would have to be true for the language to be warranted?
4. Generate candidate rival explanations, prioritizing those that could explain the same observed result through a materially different mechanism or interpretation.
5. Collapse near-duplicates. Keep at most 3 foils unless the user explicitly asks for broader exploration.
6. For each foil, separate:
   - why it competes with the proposed claim;
   - supplied evidence that supports it, if any;
   - supplied evidence that weakens it, if any;
   - evidence that is still `UNKNOWN`;
   - the most useful `DISCRIMINATOR`.
7. Rank foils by **decision relevance**, not rhetorical cleverness. Prefer a foil that would materially change the permissible claim over one that merely adds a minor caveat.
8. Identify any declaration in an existing contract that would be unsafe to mark complete until a discriminator is checked.
9. Stop. Do not convert the foil exercise into a new scientific verdict, a rewritten claim, or a completed contract.

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

Do not present a foil from one of these families as applicable unless it is at least compatible with the supplied context. If the context is too thin, say that the foil is generic and untested.

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
   Why it competes: ...
   Evidence for: ... | none supplied
   Evidence against: ... | none supplied
   UNKNOWN: ...
   DISCRIMINATOR: ...

2. FOIL — ...
   Why it competes: ...
   Evidence for: ... | none supplied
   Evidence against: ... | none supplied
   UNKNOWN: ...
   DISCRIMINATOR: ...

Contract implications:
- ...

Residual uncertainty:
- ...
```

If no materially useful foil can be generated from the available context, say so. Do not manufacture one to fill the template.

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

## Safety boundaries

- Do not treat a foil as refutation.
- Do not treat a plausible explanation as observed evidence.
- Do not claim the strongest foil is the true explanation.
- Do not infer missing diagnostics from domain conventions.
- Do not rewrite a blocked claim into softer language and call it approved.
- Do not use a mechanically `READY` contract to dismiss unresolved foils.
- Do not use unresolved foils to claim the original assertion is false.
- Do not generate `READY`, `REVIEW`, or `BLOCK`; only `claim-contract` owns those verdicts.
- Do not expand into open-ended EDA, model selection, or method recommendation unless the user explicitly asks for that separate work.

## Success looks like

- The proposed claim survives contact with its strongest plausible rival interpretations before publication.
- Observed evidence remains distinct from generated hypotheses.
- Every retained foil names a concrete discriminator instead of ending as a vague caveat.
- The packet is small enough to use as a pre-validation gate.
- Missing evidence remains missing.
- The downstream contract becomes more honest without making `claim-foil` look like a scientist or validator.
