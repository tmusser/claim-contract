# Claim Implicit — operator example

This packet uses only [`examples/onboarding_conversion/contract.yaml`](../../examples/onboarding_conversion/contract.yaml). It does **not** assume any additional study, deployment decision, diagnostic outcome, or evidence file.

The goal is to make the most consequential unstated **propositions** visible without turning them into established facts. It is deliberately different from the [claim-foil example](../claim-foil/EXAMPLE.md), which searches for competing explanations of the same reported pattern.

## Source inventory

**Explicit claim, exact wording:** “The onboarding redesign improved seven-day activation by 8%.” [`claim.text`]

**Explicit operator decision:** none supplied. The input contains no request to ship or expand the redesign.

**DECLARED (not independently verified):**

- `claim.type: causal`; population `new users`; comparison `pre_launch` versus `post_launch`; time window `2026-04-01/2026-06-30`. [`claim`]
- Design `observational_before_after`; `evidence.estimate.value: 0.08` on `relative` scale, with declared baseline `0.25`. [`evidence.design`, `evidence.estimate`]
- Metric definition `Users activated within seven days / eligible new users`. The contract **declares** `metric_definition_locked: true`, not that an independent audit found invariance. [`claim.metric.definition`, `evidence.checks.metric_definition_locked`]
- `composition_stability_assessed: false`, `identifying_assumptions_documented: false`, `treatment_assignment_validated: false`, and `uncertainty: null`. [`evidence.checks`, `evidence.uncertainty`]

**OBSERVED:** No independently inspected analysis or executed diagnostic is supplied in this example. The declarations above are facts *about the input document*, not confirmations of the experiment's results.

## Candidate inventory

### IC-01 — WARRANT: Attribution

- **IMPLICIT_CANDIDATE:** Other concurrent changes or secular trends do not materially account for the pre/post activation difference attributed to the redesign.
- **Trigger:** The exact phrase “redesign improved” and `claim.type: causal` paired with `evidence.design: observational_before_after`.
- **Why it matters / if false:** The causal interpretation would be unwarranted. A descriptive period difference might still be reportable, but would be a **different claim** requiring its own validation.
- **What is declared or observed:** A relative estimate of `0.08` is declared; `identifying_assumptions_documented: false` and `treatment_assignment_validated: false` are also declared. No causal verification was supplied.
- **UNKNOWN:** Whether evidence distinguishes the redesign effect from concurrent time-related changes.
- **CHECK:** Inspect actual design and timing evidence that separates redesign exposure from calendar-time changes, including whatever comparison or identifying assumptions the analysis truly used. Do not invent such a comparison.
- **Suggested operator choice:** **TEST** — request the identifying evidence before relying on the causal wording.

### IC-02 — WARRANT: Population comparability

- **IMPLICIT_CANDIDATE:** Differences in the mix of eligible new users across the stated pre/post periods do not materially explain the reported activation difference.
- **Trigger:** `claim.population: new users`, `claim.comparison`, and `evidence.checks.composition_stability_assessed: false`.
- **Why it matters / if false:** A change in who enters the denominator could account for an aggregate activation difference without the redesign causing it.
- **What is declared or observed:** The pre/post comparison and the explicitly `false` composition-assessment flag are declared. This flag is **not evidence that composition actually changed**.
- **UNKNOWN:** Whether the composition of eligible users changed on attributes relevant to activation.
- **CHECK:** Compare pre/post eligible-user composition on predeclared, relevant dimensions if those data are available; inspect whether any shift is large enough to materially alter the stated interpretation. No threshold or result is assumed.
- **Suggested operator choice:** **TEST** — keep this distinct from the broader attribution question so a concrete diagnostic can be requested.

### IC-03 — WARRANT: Comparable measurement

- **IMPLICIT_CANDIDATE:** The pre/post seven-day activation numerator and eligible-user denominator measure the same underlying event and eligibility rule throughout the stated window.
- **Trigger:** `claim.metric.definition`, the pre/post comparison, and the **declaration** `evidence.checks.metric_definition_locked: true`.
- **Why it matters / if false:** A changed measurement rule could create an apparent difference that is not a like-for-like change in activation.
- **What is declared or observed:** The document declares a locked metric definition. It provides no independently checked instrumentation or data lineage evidence.
- **UNKNOWN:** Whether raw event instrumentation, eligibility logic, and reporting windows actually remained comparable.
- **CHECK:** Inspect the metric implementation or a retained metric-definition audit for the pre/post periods, checking both numerator and denominator behavior. Do not mark the metric check false merely because independent evidence was not supplied.
- **Suggested operator choice:** **CLARIFY** — ask what evidence underlies the declared locked-definition check before treating it as independently established.

## Rejected candidates

- **“Shipping the redesign will improve future activation.”** Rejected: the input makes no shipping recommendation or future-population projection; it would invent a `DECISION_BRIDGE` and `SCOPE_TRANSFER`.
- **“The estimate is statistically significant.”** Rejected: `uncertainty: null` does not imply significance, and significance is not an implicit factual claim licensed by the available inputs.
- **“The pre/post populations changed.”** Rejected as a fact: `composition_stability_assessed: false` means not assessed in the declaration, not an observed change. `claim-foil` may consider composition shift as a **rival hypothesis**, but that is different from this warrant inventory.

## Operator next move

The operator can prioritize a design/attribution check, a composition comparison, and a metric-definition audit. The inventory does not choose statistical methods, fabricate evidence, or rewrite the claim.

**Promotion boundary:** These are packet-local `IC-##` candidates only. No `CCL-###` ledger ID, claim DAG `REQUIRES` edge, assumption lifecycle status, contract check, or `READY`/`REVIEW`/`BLOCK` verdict is created or changed. If adopted, a candidate must pass the destination artifact's separate declaration and validation workflow.
