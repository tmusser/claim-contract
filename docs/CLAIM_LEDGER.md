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

## Creation provenance

Ledger schema `1.1` records the context in which a claim was frozen, separately from later
evidence and adjudication.

Each claim has a `provenance` block:

- `generated_at` — the timestamp when the claim and judge contract were actually generated
  or frozen, when that timestamp is known. Use `null` for legacy claims whose true
  generation time was not retained; do not substitute a later commit timestamp.
- `recorded_at` — the timestamp when the claim first entered a durable ledger or equivalent
  retained record.
- `origin_refs` — durable references to the source of the claim, such as a conversation
  artifact, issue, pull request, commit, or other retained record.
- `context_snapshot.repository_revision` — the full repository commit SHA that anchors the
  surrounding repository state used to understand the claim.
- `context_snapshot.refs` — the specific files or artifacts that materially shaped the claim
  or judge contract. Repository-relative paths are interpreted at the recorded revision,
  not at whatever happens to be on `main` later.
- `context_snapshot.note` — a short provenance note, including any known gaps or backfill
  limitations.

Creation provenance is not evidence for the claim. It exists so a later analyst or agent can
reconstruct **what was known, what repository state existed, and when the claim entered the
durable record** without treating today's mutable files as historical truth.

Treat creation provenance as frozen metadata. If a historical field cannot be established,
record the gap explicitly rather than inferring it. Do not rewrite provenance merely because
later evidence or repository changes make a different origin story more convenient.

The original CCL-001 through CCL-003 entries predate schema `1.1`. Their `recorded_at` and
repository revision are backfilled from commit `0c2cea01537cf90dcc224614f2e35d4e1b2916fb`,
which first recorded the ledger on 2026-07-27. Their earlier conversational generation times
were not retained, so `generated_at` remains `null`.

## Adding a claim

1. Write one bounded claim sentence.
2. Assign the next unused stable ID, such as `CCL-004`. Never recycle IDs.
3. Freeze creation provenance before collecting the evidence intended to settle the claim:
   - record `generated_at` when known;
   - record `recorded_at` when the durable entry is created;
   - retain at least one durable `origin_ref`;
   - pin the repository context with a full commit SHA and the smallest relevant reference
     set.
4. Name the scope before collecting the evidence intended to settle the claim.
5. Record the decision impact: what would change if support or refutation is met?
6. Freeze the judge contract:
   - `support_if`
   - `refute_if`
   - `otherwise: INCONCLUSIVE`
7. Record current evidence separately from gaps and required future evidence.
8. Name the smallest useful next adjudication step.

If the claim or judge contract changes materially **after evidence has been observed**, keep
the old entry and create a new ID linked with `supersedes`. Do not move the goalposts in
place. The new claim gets its own creation provenance rather than inheriting the old claim's
timestamp or context snapshot.

## Agent adjudication

A fresh agent can judge an `OPEN` claim when the required evidence exists:

1. Read the ledger entry and its referenced evidence.
2. Use the creation provenance to reconstruct the claim's original context when historical
   interpretation matters; resolve repository-relative context refs at the recorded revision.
3. Verify that the evidence matches the recorded scope.
4. Do not infer missing results, labels, sample sizes, model settings, or benchmark details.
5. Apply `support_if` and `refute_if` exactly as written.
6. If support is met, set `SUPPORT_MET`.
7. If refutation is met, set `REFUTE_MET`.
8. If evidence was evaluated but neither condition is met, set `INCONCLUSIVE`.
9. Record the exact evidence references, date, judge identity/model, and a short note.
10. Preserve contradictory or unfavorable evidence rather than summarizing only the winning
    side.

If the evidence is incomplete, leave the claim `OPEN` rather than guessing.

## Structural validation

The live ledger uses schema `1.1`, published at
[`schemas/claim-ledger-v1.1.schema.json`](../schemas/claim-ledger-v1.1.schema.json). CI
validates that the live ledger conforms to that schema, that provenance timestamps are valid
RFC 3339 date-times when present, and that claim IDs are unique.

The original `1.0` schema remains published at
[`schemas/claim-ledger-v1.schema.json`](../schemas/claim-ledger-v1.schema.json) so historical
consumers are not silently moved onto the stricter provenance contract.

Schema validation proves only that the ledger is structurally complete. It does not prove
that the claim, evidence, thresholds, provenance narrative, or eventual judgment are
scientifically sound.
