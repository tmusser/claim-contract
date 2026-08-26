# Roadmap

This roadmap records possible directions, not promises or release commitments.

`claim-contract` should stay small. A new feature belongs only when it catches a recurring evidence-to-language failure mode using explicit, inspectable inputs.

## Near-term priorities

- Stabilize `minimum-v0.1` rule semantics and output fields.
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
- Bound generated validation reports to deterministic identities for the exact parsed contracts that produced them, with read-only saved-report verification.
- Exposed the `minimum-v0.1` rule contract as a versioned machine-readable profile manifest with rule IDs, severities, consumed fields, triggers, and known boundaries.
- Added a strict, versioned `claim-contract` to `chart-contract` handoff envelope that preserves bounded claim context, validation status, and contract identity without recommending a visualization.

## Candidate directions

These require evidence before promotion:

- Additional narrow profiles for well-defined analytical contexts.
- Explicit compatibility or diff reporting across profile-manifest versions, including any future report-to-profile binding.
- Optional downstream consumption of the bounded chart-handoff artifact without collapsing claim-contract and chart-contract responsibilities.

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
