# Roadmap

This roadmap records possible directions, not promises or release commitments.

`claim-contract` should stay small. A new feature belongs only when it catches a recurring evidence-to-language failure mode using explicit, inspectable inputs.

## Near-term priorities

- Stabilize `minimum-v0.1` rule semantics and output fields.
- Score the frozen CCL-002 `minimum-v0.1` benchmark only after its freeze revision is merged, retaining case-level outputs for independent adjudication.
- Run the frozen CCL-001 paired agent-summary evaluation only after its case set, instruction, and annotation rubric are merged; retain raw outputs and human annotations for at least two model families before independently applying the ledger judge contract.
- Expand adversarial coverage only when a recurring misuse or blind spot is observed.
- Document rule false positives and known blind spots as they are discovered.

## Completed foundations

- Added executable adversarial fixtures for false confidence, undeclared assumptions, and agent misuse.
- Locked adversarial verdicts, rule IDs, and safe/unsafe agent-summary boundaries in tests.
- Added versioned machine-readable report and error envelopes.
- Published JSON Schemas that require the scope notice, `not_evaluated`, and `scientific_validation: false`.
- Published a Draft 2020-12 JSON Schema for canonical `minimum-v0.1` input contracts while preserving rule-engine verdict semantics.
- Added structured JSON input errors and compatibility tests across every example contract.
- Added read-only verification for commit-pinned claim-ledger context references.
- Added read-only machine-readable claim-ledger `list` / `show` inspection with recorded-status filtering and an explicit no-adjudication boundary.
- Bound generated validation reports to deterministic identities for the exact parsed contracts that produced them, with read-only saved-report verification.
- Exposed the `minimum-v0.1` rule contract as a versioned machine-readable profile manifest with rule IDs, severities, consumed fields, triggers, and known boundaries.
- Bound new contract-bound reports to the semantic identity of the selected profile manifest, with saved-report drift verification and legacy profile-unbound compatibility.
- Added mechanical profile-manifest diff inspection aligned to the same semantic identity, without automatic compatibility classification.
- Added a strict, versioned `claim-contract` to `chart-contract` handoff envelope that preserves bounded claim context, validation status, and contract identity without recommending a visualization.
- Added semantic parsed-contract diff inspection with explicit field changes and verdict transitions without automatic interpretation.
- Froze a 50-case, independently labeled `minimum-v0.1` benchmark for CCL-002 with a written rubric and a scorer that binds future results to the exact corpus, labels, and profile-manifest identity.
- Froze a 30-case paired agent-summary evaluation for CCL-001 comparing bare verdict + claim text against the full report envelope, with a predeclared human annotation rubric and a scorer that computes judge-relevant rates without adjudicating the ledger claim.
- Published a versioned assumptions-ledger sidecar schema with typed assumption cards, explicit review/challenge/retirement lifecycle state, and exact contract/profile-manifest bindings without changing `minimum-v0.1` verdict semantics.
- Added an optional claim DAG sidecar with explicit claim/assumption/evidence dependencies, required-path exposure triage, and Mermaid rendering without numeric fragility scoring or scientific adjudication.
- Added a thin official GitHub Action that sets up Python and delegates contract gating to the existing CLI, preserving the same READY / REVIEW / BLOCK and `--warnings-as-errors` exit semantics.
- Unified graph and DAG tooling under the primary `claim-contract` command tree while preserving the older executables as compatibility aliases.
- Added deterministic per-rule trace inspection so agents and analysts can distinguish triggered rules, applicable passes, and non-applicable rules without changing validator verdict semantics.
- Added optional evidence receipts so applicable declared evidence fields can point to contract-bound, commit-pinned repository refs without treating path existence as evidence verification or changing READY / REVIEW / BLOCK.

## Candidate directions

These require evidence before promotion:

- Additional narrow profiles for well-defined analytical contexts.
- Optional downstream consumption of the bounded chart-handoff artifact without collapsing claim-contract and chart-contract responsibilities.
- Read-only assumptions-ledger inspection and binding verification after the sidecar format sees real use; any validator consumption of assumption records requires a separate profile/versioning decision.

Candidate features stay here. Empirical claims about whether the harness or its interfaces actually improve agent behavior, catch enough violations, or reduce overclaiming belong in the machine-readable [`claims/ledger.yaml`](claims/ledger.yaml), where support and refutation conditions are frozen before the evidence intended to settle them is observed.

## Explicit non-goals

The roadmap does not include:

- becoming an autonomous analyst or scientist;
- automatically choosing methods, models, or causal designs;
- certifying scientific validity;
- automatically rewriting claims into supposedly safe language;
- replacing statistical, domain, ethical, or peer review;
- adding rules merely to make the harness appear comprehensive.

## Promotion gate for new rules

A proposed rule should identify:

1. the concrete failure mode;
2. the exact declared inputs it consumes;
3. the intended `READY`, `REVIEW`, or `BLOCK` behavior;
4. positive, negative, and edge-case tests;
5. known false positives and what the rule cannot detect.

Rules that require hidden context or pretend to verify unobserved analysis should not be added.
