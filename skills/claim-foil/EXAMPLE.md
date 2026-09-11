# Claim Foil worked example

This example uses the existing [`examples/onboarding_conversion/contract.yaml`](../../examples/onboarding_conversion/contract.yaml) input. It does not add evidence beyond that contract.

## Input claim

> The onboarding redesign improved seven-day activation by 8%.

The declared evidence is an `observational_before_after` comparison with a relative estimate of `0.08`, baseline value `0.25`, `sample_size: 18420`, no uncertainty object, and `composition_stability_assessed: false`.

## Example output

```text
CLAIM FOIL

Proposed claim:
- The onboarding redesign improved seven-day activation by 8%.

Observed evidence:
- OBSERVED — post-launch activation is declared 8% higher on a relative scale than the pre-launch baseline. [examples/onboarding_conversion/contract.yaml: evidence.estimate]
- OBSERVED — the design is declared observational before/after. [examples/onboarding_conversion/contract.yaml: evidence.design]
- OBSERVED — composition stability is explicitly declared false. [examples/onboarding_conversion/contract.yaml: evidence.checks.composition_stability_assessed]
- OBSERVED — uncertainty is explicitly null. [examples/onboarding_conversion/contract.yaml: evidence.uncertainty]

Central burden:
- The observed pre/post change must be attributable to the onboarding redesign strongly enough to warrant causal language, rather than to another difference between the two periods or populations.

Foils:
1. FOIL — the post-launch population differed materially from the pre-launch population.
   Admission: compatible + competitive + distinct + discriminable + decision-relevant
   Why it competes: a composition shift could change activation even if the redesign had no causal effect.
   Evidence for: none supplied.
   Evidence against: none supplied.
   UNKNOWN: whether activation-relevant user characteristics or acquisition mix were stable across periods.
   DISCRIMINATOR: compare the declared pre/post populations on preselected activation-relevant composition variables or another predeclared composition diagnostic.
   Resolution signal: material composition movement aligned with the activation change would strengthen this foil; stable composition on the predeclared diagnostics would weaken it but would not establish causality.

2. FOIL — another time-varying change coincident with launch explains some or all of the observed increase.
   Admission: compatible + competitive + distinct + discriminable + decision-relevant
   Why it competes: a before/after design does not by itself isolate the redesign from concurrent events or secular movement.
   Evidence for: none supplied; compatibility with the declared design is not evidence for the foil.
   Evidence against: none supplied.
   UNKNOWN: whether concurrent product, acquisition, seasonality, or environmental changes were ruled out.
   DISCRIMINATOR: inspect supplied or newly produced evidence that separates redesign exposure from calendar time, or directly tests the predeclared identifying assumptions of an eligible design.
   Resolution signal: evidence that the change tracks redesign exposure rather than calendar time would weaken this foil; a coincident shift not specific to redesign exposure would strengthen it.

Contract implications:
- Do not mark composition stability as assessed until the diagnostic is actually performed.
- Do not treat either foil as proof that the redesign had no effect.
- The foil exercise does not change the contract verdict; validate the declared fields with claim-contract.

Assumption implications:
- None can be promoted into assumptions-ledger lifecycle state from this packet alone. If later evidence is used to review or challenge a recorded assumption, use the ledger's explicit lifecycle workflow.

Residual uncertainty:
- The supplied evidence cannot distinguish the causal claim from the retained foils.
```

## Why there are only two foils

The skill defaults to the strongest materially distinct rivals, not a fixed quota. The contract declares the metric definition locked, so this example does not invent a metric-definition failure merely to produce a third foil. A generated foil should earn its place by passing the admission gate.

## Why `none supplied` is not evidence against

Neither retained foil is weakened merely because the contract contains no evidence for it. The absence of supplied evidence means the relevant discriminator remains unknown; it does not establish that the rival mechanism was searched for and ruled out.
