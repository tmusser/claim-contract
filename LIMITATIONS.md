# Limitations and interpretation boundaries

`claim-contract` is a deterministic claim harness. It is intentionally narrower than scientific or analytical review.

## The meaning of READY

`READY` means:

> The submitted fields did not trigger any implemented `REVIEW` or `BLOCK` rule in the selected contract profile.

It does **not** mean:

- the claim is true;
- the data are accurate or representative;
- the metric is substantively meaningful;
- the analysis code is correct;
- the model is well specified;
- the uncertainty estimate was computed correctly;
- causal assumptions hold in the real world;
- the result is reproducible;
- the finding generalizes;
- the claim is material, useful, ethical, or decision-worthy;
- a qualified human reviewer would approve it.

## Declared evidence is not verified evidence

The harness consumes declarations. It does not currently execute notebooks, inspect SQL, rerun models, validate raw rows, or verify provenance systems.

A user or agent can incorrectly declare that a check was completed. The harness may then produce a cleaner result than the underlying work deserves.

For that reason, outputs use the phrase **declared minimum contract** rather than “validated analysis.”

## Rules are incomplete and contestable

The initial profile covers a small set of common failure modes. It cannot encode every valid analytical design or every domain-specific exception.

A `BLOCK` may be conservative. A `READY` may miss a serious flaw. A `REVIEW` is not a recommendation to publish.

## Rule-specific blind spots

The multiplicity rule can only evaluate what the contract declares. It cannot discover undisclosed outcomes, segment fishing, repeated model attempts, abandoned hypotheses, or other hidden researcher degrees of freedom.

The magnitude-language rule uses a narrow vocabulary heuristic. It may miss domain-specific magnitude language, and it may flag words whose meaning depends on context. Supplying a numeric estimate satisfies the declared rule; it does not prove that the chosen scale is substantively appropriate.

These rules improve traceability. They do not reconstruct the full analytical process.

## Determinism is not expertise

Deterministic output improves reproducibility of the gate. It does not create domain knowledge or statistical judgment.

Theatrical risk is real: schemas, rule IDs, and colored verdicts can create extra confidence. Consumers should treat formal output as a checklist with receipts, not as a scientific credential.

## Intended use

Appropriate uses include:

- CI-style checks for obvious evidence/language mismatches;
- agent guardrails before drafting reports or charts;
- reproducible review prompts for human analysts;
- auditable records of which minimum checks were declared.

Inappropriate uses include:

- unattended publication of consequential findings;
- regulatory, medical, legal, safety-critical, or high-stakes decisions without qualified review;
- certifying causal conclusions;
- replacing peer review, statistical review, or domain review;
- ranking analysts or analyses by verdict alone.

## Human responsibility

The person or team sharing the claim remains responsible for the analysis and its consequences. `claim-contract` does not transfer accountability to software.
