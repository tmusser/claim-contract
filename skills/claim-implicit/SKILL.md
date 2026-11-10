---
name: claim-implicit
description: Enumerate a small, source-anchored inventory of unstated propositions that materially affect how an operator interprets an analytical claim or an explicitly proposed decision, without treating candidates as facts, dependencies, or contract verdicts.
---

# Claim Implicit

## Purpose

Surface the **unstated claims an operator may be relying on** when interpreting an analytical assertion or following an explicitly proposed action. Turn a hidden warrant into an inspectable, falsifiable question with a source anchor and a next check.

This is **operator triage**, not automated inference, a validator, or a claim ledger. A candidate is a proposed proposition to investigate, **not a fact implied as true by the input**. The skill does not create `CCL-###` IDs, write ledger entries, or produce `READY`, `REVIEW`, or `BLOCK`.

Unlike `claim-foil` (rival explanations for the same observation), this skill asks: *What unstated proposition would need to hold to justify this particular interpretation, extension, or proposed decision?* A foil might subsequently challenge a retained proposition, but it must not be silently reclassified as an observed fact.

## Hard boundaries

1. **Separate stated from inferred.** Copy the explicit claim and any decision recommendation verbatim. Label every new proposition `IMPLICIT_CANDIDATE`; never put one in `OBSERVED`, `DECLARED`, or a validated-report field.
2. **Anchor the trigger.** Each candidate must link to a supplied claim clause, contract field, recommendation, or operator-stated decision with the narrowest available locator. Generic domain knowledge alone cannot trigger a specific candidate.
3. **Respect evidence semantics.** `DECLARED` means the source reports a field or a completed check, **not** that the measurement or check was independently verified. An explicit `false`, a `null`, and an absent field are distinct.
4. **No invented decisions.** Only propose a decision-bridge claim when the operator or source actually expresses the decision. Do not turn a claim about an observed effect into an unstated recommendation to ship a product.
5. **No unsupported scope transfer.** A statement about new users in one period is not automatically a claim about other users, other periods, or the future. Scope extension candidates require an actual extension in supplied language.
6. **No auto-promotion.** Candidate IDs (`IC-01`, etc.) are packet-local, not durable claim ledger IDs. Do not add candidates to `claims/ledger.yaml`, `claims/graph.yaml`, a claim DAG, or an assumptions ledger without explicit human adoption and those artifacts' own contracts.
7. **No verdict laundering.** Never generate or alter `READY`, `REVIEW`, `BLOCK`, ledger status, DAG `attention`, or an assumption-review state. The absence of candidates does not endorse the explicit claim.
8. **No quota filling.** Default to at most **five** decision-relevant candidates; zero is valid. Prefer one discriminating question to a catalog of generic caveats.

## Inputs

Use the actually supplied material, not guessed project context:

- proposed claim text and its source locator;
- any **explicit** decision or broader-scope recommendation and its locator;
- analytical contract fields (claim type, population, metric, window, comparison, design, estimates, checks, caveats);
- observed analysis, citations, tests, and provenance when supplied;
- optionally, existing foils, DAG nodes, assumptions cards, or ledger records for cross-referencing **only when the mapping is explicit**.

If a claim or decision is not supplied, request it or produce a scoped inventory with the available material. Never fabricate an unseen outcome or business decision.

## Candidate families

Use these as **search lenses**, not as an obligatory checklist:

- `WARRANT` — a substantive premise needed for the exact claim's interpretation, such as comparison comparability or causal attribution.
- `DECISION_BRIDGE` — an additional proposition needed to go from the stated analysis to an **explicitly** proposed operator action, such as net benefit or acceptable trade-offs.
- `SCOPE_TRANSFER` — an additional proposition needed to make an **explicitly** proposed extrapolation across populations, settings, metrics, or time.

Do not count a copied statement, a check that merely repeats a source field, or a generic methodological admonition as an implicit claim. An unstated proposition must be articulable as something potentially false.

## Candidate admission gate

Retain a candidate only when **all** of these hold:

1. **Unstated:** The proposition is not already asserted explicitly in the supplied claim or recommendation.
2. **Source-tethered:** A precise input clause or field explains why this proposition matters here.
3. **Material:** If it fails, the claimed interpretation, the **stated** decision, or the **stated** scope extension would materially change.
4. **Inspectable:** Name an observable, artifact, comparison, or human judgment that could help evaluate it. Avoid promising complete verification when that is not possible.
5. **Distinct:** It does not restate another candidate or merely paraphrase a `claim-foil` rival explanation.

If the supplied context is too thin, retain none and name the missing context. Lack of a source anchor is a reason to reject a candidate, not to provide a made-up citation.

## Workflow

1. Quote the explicit claim **exactly**. Record any proposed decision separately; otherwise mark `decision: none supplied`.
2. Inventory only relevant `DECLARED` fields and independently `OBSERVED` evidence. Give each an exact locator. If no locators exist, state `[supplied context; locator unavailable]`.
3. Identify the narrow interpretation actually requested. Distinguish retrospective description, causal explanation, and prospective action. Preserve the original claim type.
4. Propose unstated candidate propositions from the three families, with each trigger and `if false` consequence.
5. Run the admission gate. Drop unsupported decision bridges, unwarranted extrapolations, irrelevant possibilities, and semantic duplicates.
6. For each retained candidate, output its precise positive proposition, trigger locator, supporting **declarations** (if any), `UNKNOWN` elements, the smallest useful check, and **suggested operator choice** (`TEST`, `CLARIFY`, `CAVEAT`, `DEFER`, or `DISCARD`). This is a recommendation for review, not a performed action.
7. Sort by how strongly an unresolved candidate could change the supplied interpretation or decision—not by rhetorical plausibility, numeric confidence, or graph position.
8. Explicitly list tempting **rejected** candidates if that guards against a likely mistaken inference.
9. Stop. Do not create a new contract, rewrite the claim, run a verdict, or update source artifacts without a separate operator instruction.

## Output contract

Use a compact review packet with these labels:

```text
IMPLICIT CLAIM INVENTORY — CANDIDATES ONLY

Explicit claim: "..." [source locator]
Explicit operator decision: "..." [locator] | none supplied
Source inventory:
- DECLARED — ... [locator]
- OBSERVED — ... [locator] | none independently supplied

Candidate IC-01 [WARRANT | DECISION_BRIDGE | SCOPE_TRANSFER]
- IMPLICIT_CANDIDATE: ... (a falsifiable proposition, not a question)
- Trigger: ... [locator]
- Why it matters / if false: ...
- What is declared or observed: ... | none supplied
- UNKNOWN: ...
- CHECK: ... (concrete, inspectable, bounded)
- Suggested operator choice: TEST | CLARIFY | CAVEAT | DEFER | DISCARD — why

Rejected candidates: ... | none
Promotion boundary: IC IDs are local suggestions. No ledger or DAG entry, contract-field update,
assumption lifecycle change, scientific validation, or verdict has occurred.
```

When no candidate passes the gate:

```text
Candidates:
- None retained from the supplied context without speculation.
```

That means only that this pass produced no admissible suggestions.

## Operator handoff and optional promotion

The operator can use a packet to decide what needs clarification, testing, caveating, or dropping. If a candidate is adopted as an **analytical claim**, create a distinct contract for its actual wording and declared evidence, then run the normal validator. If a candidate warrants a **product/research ledger claim**, first freeze a scoped, independently judgeable `support_if`/`refute_if` contract with creation provenance per `docs/CLAIM_LEDGER.md`. If it becomes an **assumption** or **DAG dependency**, declare that relationship explicitly using the respective schema and lifecycle. None of these promotions happen automatically.

Do not infer a `REQUIRES` edge from a skill-generated warrant: the DAG records author-declared prerequisites; the graph records relevance, not logical entailment. No proposed candidate or check proves the source claim scientifically valid.

See [EXAMPLE.md](EXAMPLE.md) for an operator packet over a real repository fixture.
