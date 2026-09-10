# Assumptions ledger

An assumptions ledger is a bound sidecar artifact for making analytical premises explicit, typed, and reviewable without pretending to prove them.

The v1 artifact is intentionally separate from both the normal analytical contract and the repository-level open claim ledger:

- the analytical contract asks whether declared evidence satisfies implemented evidence-to-language rules;
- the assumptions ledger records the premises on which interpretation depends and their review lifecycle;
- the open claim ledger freezes product/research claims and future evidence thresholds.

These are different contracts and should not be collapsed into one status system.

> An assumption can be explicit and reviewed without being true.

## Why a separate artifact

`minimum-v0.1` currently represents quasi-experimental assumption documentation with the boolean `evidence.checks.identifying_assumptions_documented`.

That boolean is useful for a narrow rule gate, but it cannot answer:

- which assumptions were actually recorded;
- what analytical role each assumption plays;
- where each assumption applies;
- what evidence or diagnostic was inspected;
- what would invalidate the assumption;
- whether a reviewer challenged it later;
- which exact contract and profile semantics the assumptions were written for.

The assumptions ledger makes those details inspectable without changing the meaning of `READY`, `REVIEW`, or `BLOCK`.

## Current validator boundary

The v1 ledger is **not consumed by `minimum-v0.1` validation**.

`CC302` still reads only `evidence.checks.identifying_assumptions_documented`. A ledger with a `CHALLENGED` assumption does not automatically add a finding, downgrade a verdict, or set that boolean to `false`. Conversely, a structurally valid assumptions ledger does not prove that the boolean should be `true`.

Any future rule that consumes assumption records is a separate profile/versioning decision and must earn its place through the normal rule-promotion gate.

## Bound identity

Every ledger carries both identities already used by contract-bound reports:

- `contract.input_binding` uses `parsed-contract-v1` to bind the exact parsed analytical contract;
- `contract.profile_manifest_binding` uses `profile-manifest-semantics-v1` to bind the exact machine-readable profile semantics.

These digests are content identities, not authentication. Matching hashes do not prove that the analysis, assumption records, evidence, or review are correct. A mismatch means the ledger is detached from the contract or profile semantics it claims to describe and should not be silently rebound.

The ledger also repeats `claim_text` so a human reviewer can identify the assertion without opening the contract. Tests lock the bundled example's claim text and both bindings to its companion contract and the installed profile manifest.

## Assumption card

Each assumption has a stable lower-snake-case ID and a bounded semantic core:

```yaml
id: no_precise_cutoff_manipulation
aliases:
  - no_sorting_at_cutoff
category: identifying
role: regression discontinuity assignment integrity
statement: >-
  Subjects cannot precisely manipulate the running variable to sort around the
  eligibility cutoff in a way that invalidates local comparison.
scope: users near the declared cutoff during the analysis window
status: CHALLENGED
invalidation_trigger: >-
  Evidence of precise control of the running variable that changes assignment.
```

The full card also records:

- current evidence references, validation method, last check time, and note;
- an explicit caveat when useful;
- creation provenance through `recorded_at` and `source_refs`;
- lifecycle records for review, challenge, and retirement;
- `supersedes` when a materially changed assumption replaces an older stable ID.

The schema intentionally does not include a generic numeric confidence score. Review state and evidence should remain inspectable rather than being compressed into a precision-looking number with unclear semantics.

## Categories

The v1 categories are deliberately small:

| Category | Intended use |
| --- | --- |
| `identifying` | Premises required for causal or quasi-experimental identification. |
| `measurement` | Assumptions about metrics, instrumentation, labels, or measurement validity. |
| `sampling` | Assumptions about inclusion, selection, representativeness, or missingness mechanisms. |
| `model` | Assumptions required by a statistical or predictive model interpretation. |
| `operational` | Assumptions about implementation, exposure, assignment, timing, or data-generation operations. |
| `interpretive` | Bounded premises needed to translate an estimate into the proposed language or decision context. |

A category is organization metadata. It does not select a statistical method or certify that the assumption is necessary or sufficient.

## Lifecycle

The lifecycle records **review state**, not truth state:

| Status | Required state | Meaning |
| --- | --- | --- |
| `OPEN` | no review, challenge, or retirement record | Recorded but not yet reviewed. |
| `REVIEWED` | review record | A named reviewer inspected the assumption and recorded evidence/notes. |
| `CHALLENGED` | review + challenge records | A reviewed assumption has a material unresolved objection. |
| `RETIRED` | retirement record | No longer active for the bound analysis; not a statement that it was true or false. |

Lifecycle transitions are not automatic. Schema validation checks structural consistency only; it does not inspect evidence and decide that an assumption deserves a new status.

If the `statement`, `scope`, analytical `role`, or `invalidation_trigger` changes materially after review evidence has been observed, create a new stable ID, set `supersedes`, and retire the old card. Do not silently rewrite the premise while preserving a favorable review history.

## Evidence boundary

`evidence.refs` and lifecycle `evidence_refs` are references supplied by the author/reviewer. The v1 schema does not fetch those references, verify that they exist, judge diagnostic quality, or determine whether they establish the assumption.

Use `CHALLENGED` when a material unresolved objection is already known. Preserve contradictory evidence rather than summarizing only the favorable side.

## Worked example

The synthetic fixture in [`examples/assumptions_ledger/`](../examples/assumptions_ledger/) binds a quasi-experimental causal contract to two identifying assumptions:

- `continuity_at_cutoff` is `REVIEWED` with an explicit caveat;
- `no_precise_cutoff_manipulation` is `CHALLENGED` because the synthetic density diagnostic shows unresolved bunching near the cutoff.

The companion contract still has `identifying_assumptions_documented: true`. That is deliberate: the assumptions are documented, but one remains challenged. `minimum-v0.1` continues to require qualified human review through `CC305` and does not interpret the ledger as an automatic causal-validity judgment.

## What v1 does not do

The assumptions ledger does not:

- prove or refute an assumption;
- execute diagnostics;
- choose a design, model, test, or identification strategy;
- mutate an analytical contract;
- change `READY`, `REVIEW`, or `BLOCK`;
- replace qualified analytical or domain review;
- authenticate the author, reviewer, evidence, or bindings;
- infer missing assumptions from the analysis;
- turn a `REVIEWED` card into scientific validation.

Published schema: [`schemas/assumptions-ledger-v1.schema.json`](../schemas/assumptions-ledger-v1.schema.json).
