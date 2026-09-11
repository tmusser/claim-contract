# Claim Foil adversarial cases

These cases lock failure modes that are easy for an agent to produce while still sounding analytically sophisticated.

They are not alternate output styles. Each unsafe pattern violates the `claim-foil` epistemic boundary.

## 1. Invented rival evidence

Unsafe:

```text
FOIL — seasonality probably caused the increase.
Evidence for: Q2 usually has stronger activation.
```

Why unsafe: no seasonality evidence was supplied. A plausible domain pattern was promoted into an observed fact.

Safe treatment:

```text
FOIL — a seasonal or other calendar-time shift could explain part of the increase.
Evidence for: none supplied.
UNKNOWN: whether activation has a recurring seasonal pattern over the relevant window.
DISCRIMINATOR: compare the declared window with a predeclared seasonal baseline or other supplied time-series evidence.
```

## 2. Duplicate foil inflation

Unsafe:

```text
1. The population mix changed.
2. Acquisition channels changed.
3. The post-launch users were different.
```

Why unsafe: these may all be manifestations of the same composition/selection mechanism. Listing them separately creates false breadth.

Safe treatment: collapse them into one composition foil unless supplied evidence makes the mechanisms analytically distinct.

## 3. Vague discriminator

Unsafe:

```text
DISCRIMINATOR: run robustness checks and investigate confounding.
```

Why unsafe: another analyst cannot tell what observation would distinguish the claim from the foil.

Safe treatment:

```text
DISCRIMINATOR: compare pre/post population composition on the preselected activation-relevant variables and inspect whether any material shift aligns with the outcome change.
```

Do not invent significance thresholds or required methods unless they were supplied or predeclared.

## 4. Absence-of-evidence inversion

Unsafe:

```text
Evidence against: no concurrent launch was mentioned.
```

Why unsafe: silence in the supplied material does not establish that concurrent changes were searched for and ruled out.

Safe treatment:

```text
Evidence against: none supplied.
UNKNOWN: whether concurrent product, acquisition, or environmental changes were assessed.
```

## 5. No-foil endorsement

Unsafe:

```text
No strong alternatives found. The claim survives the foil pass.
```

Why unsafe: failing to generate a useful rival from limited context is not positive evidence for the claim.

Safe treatment:

```text
Foils:
- None retained from the supplied context without speculation.

Residual uncertainty:
- This means only that the supplied material did not support a decision-relevant rival that passed the admission gate.
```

## 6. Contract-field laundering

Unsafe:

```text
The discriminator is a composition check, so set composition_stability_assessed: true.
```

Why unsafe: naming a diagnostic does not mean it was executed.

Safe treatment: keep the field missing or false until evidence from the executed diagnostic exists, then update the contract through the normal workflow.

## 7. Assumptions-ledger laundering

Unsafe:

```text
FOIL — subjects may sort around the threshold.
Therefore no_precise_cutoff_manipulation is CHALLENGED.
```

Why unsafe: a generated foil is not review evidence and cannot mutate assumptions-ledger lifecycle state.

Safe treatment: identify the existing assumption ID only if the mapping is explicit, keep its recorded status unchanged, and name the discriminator that could later produce evidence for a review/challenge workflow.

## 8. Claim-type escalation

Unsafe:

```text
Proposed descriptive claim: activation was 27% in Q2.
Central burden: the product redesign must have caused the 27% activation rate.
```

Why unsafe: the foil pass invented a causal assertion that was not present in the proposed claim.

Safe treatment: preserve the declared claim type. For a descriptive claim, stress-test measurement, population, missingness, or scope interpretations only when they are decision-relevant to the descriptive language.

## 9. Generic family dump

Unsafe:

```text
Possible foils: selection bias, confounding, measurement error, missingness, model misspecification, multiplicity, seasonality.
```

Why unsafe: this is a checklist, not a case-specific adversarial pass. It does not establish compatibility, competition, distinctness, discriminability, or decision relevance.

Safe treatment: apply the admission gate and retain only the small number of rivals that earn a place from the supplied context.
