# Roadmap

This roadmap records possible directions, not promises or release commitments.

`claim-contract` should stay small. A new feature belongs only when it catches a recurring evidence-to-language failure mode using explicit, inspectable inputs.

## Near-term priorities

- Stabilize `minimum-v0.1` rule semantics and output fields.
- Expand adversarial coverage only when a recurring misuse or blind spot is observed.
- Improve machine-readable interoperability without weakening the scope notice.
- Document rule false positives and known blind spots as they are discovered.

## Completed foundations

- Added executable adversarial fixtures for false confidence, undeclared assumptions, and agent misuse.
- Locked adversarial verdicts, rule IDs, and safe/unsafe agent-summary boundaries in tests.

## Candidate directions

These require evidence before promotion:

- Versioned JSON Schema validation for contract documents.
- Additional narrow profiles for well-defined analytical contexts.
- Optional provenance adapters that verify declared artifacts actually exist.
- A shared handoff format from `claim-contract` to `chart-contract`.
- Better reporting for profile/rule compatibility across versions.

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
