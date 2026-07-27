# Open claim ledger

`claims/ledger.yaml` is the repository's durable queue of **important claims that have not
been earned yet but can be judged from future evidence**.

It exists to stop two opposite failures:

1. a useful hypothesis disappears into chat, an issue, or a roadmap note before anyone
   defines what evidence would settle it;
2. a plausible hypothesis slowly turns into README language without a predeclared evidence
   threshold.

> A ledger claim must be able to lose.

## What belongs here

Add a claim only when all of the following are true:

- it matters beyond one implementation task or session;
- it is bounded enough to support or refute within a named scope;
- the required evidence can realistically be produced and inspected;
- the answer would change product positioning, rule design, documentation, or roadmap
  priority;
- a fresh agent could apply the recorded judge contract without reconstructing the original
  conversation.

Do not use the ledger for TODOs, feature ideas, routine unknowns, or claims so broad that no
practical evidence could count against them.

## Two different contracts

The ledger is deliberately separate from the normal `claim-contract validate` input.

- An **analytical claim contract** asks whether declared analytical evidence satisfies the
  implemented minimum evidence-to-language rules. Its verdict is `READY`, `REVIEW`, or
  `BLOCK`.
- A **ledger judge contract** freezes what future evidence would count as support or
  refutation for a repository-level product or research claim. Its status is `OPEN`,
  `SUPPORT_MET`, `REFUTE_MET`, `INCONCLUSIVE`, or `RETIRED`.

Neither status system is scientific validation.

## Status meanings

- `OPEN` — the claim is judgeable, but the required evidence has not yet been evaluated.
- `SUPPORT_MET` — the frozen scoped support condition was met.
- `REFUTE_MET` — the frozen scoped refutation condition was met.
- `INCONCLUSIVE` — evidence was evaluated, but neither frozen condition was met cleanly.
- `RETIRED` — the claim is no longer decision-relevant. This is not a truth judgment.

Use `SUPPORT_MET` and `REFUTE_MET` rather than `PROVEN` or `FALSE`. A ledger judgment says
what happened under the recorded scope and rule; it does not establish universal truth.

## Adding a claim

1. Write one bounded claim sentence.
2. Assign the next unused stable ID, such as `CCL-004`. Never recycle IDs.
3. Name the scope before collecting the evidence intended to settle the claim.
4. Record the decision impact: what would change if support or refutation is met?
5. Freeze the judge contract:
   - `support_if`
   - `refute_if`
   - `otherwise: INCONCLUSIVE`
6. Record current evidence separately from gaps and required future evidence.
7. Name the smallest useful next adjudication step.

If the claim or judge contract changes materially **after evidence has been observed**, keep
the old entry and create a new ID linked with `supersedes`. Do not move the goalposts in
place.

## Agent adjudication

A fresh agent can judge an `OPEN` claim when the required evidence exists:

1. Read only the ledger entry and its referenced evidence.
2. Verify that the evidence matches the recorded scope.
3. Do not infer missing results, labels, sample sizes, model settings, or benchmark details.
4. Apply `support_if` and `refute_if` exactly as written.
5. If support is met, set `SUPPORT_MET`.
6. If refutation is met, set `REFUTE_MET`.
7. If evidence was evaluated but neither condition is met, set `INCONCLUSIVE`.
8. Record the exact evidence references, date, judge identity/model, and a short note.
9. Preserve contradictory or unfavorable evidence rather than summarizing only the winning
   side.

If the evidence is incomplete, leave the claim `OPEN` rather than guessing.

## Structural validation

The ledger format is published at
[`schemas/claim-ledger-v1.schema.json`](../schemas/claim-ledger-v1.schema.json). CI validates
that the live ledger conforms to the schema and that claim IDs are unique.

Schema validation proves only that the ledger is structurally complete. It does not prove
that the claim, evidence, thresholds, or eventual judgment are scientifically sound.
