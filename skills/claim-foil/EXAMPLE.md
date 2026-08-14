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
- OBSERVED — post-launch activation is declared 8% higher on a relative scale than the pre-launch baseline. [examples/onboarding_conversion/contract.yaml]
- OBSERVED — the design is observational before/after. [examples/onboarding_conversion/contract.yaml]
- OBSERVED — composition stability was not assessed. [examples/onboarding_conversion/contract.yaml]
- OBSERVED — no uncertainty information was supplied. [examples/onboarding_conversion/contract.yaml]

Central burden:
- The observed pre/post change must be attributable to the onboarding redesign strongly enough to warrant causal language, rather than to another difference between the two periods or populations.

Foils:
1. FOIL — the post-launch population differed materially from the pre-launch population.
   Why it competes: a composition shift could change activation even if the redesign had no causal effect.
   Evidence for: composition stability is explicitly unassessed.
   Evidence against: none supplied.
   UNKNOWN: whether relevant user characteristics or acquisition mix were stable across periods.
   DISCRIMINATOR: compare pre/post composition on activation-relevant covariates or another predeclared composition diagnostic.

2. FOIL — another time-varying change coincident with launch explains some or all of the observed increase.
   Why it competes: a before/after design does not by itself isolate the redesign from concurrent events or secular movement.
   Evidence for: none supplied; this foil is compatible with the declared observational before/after design.
   Evidence against: none supplied.
   UNKNOWN: whether concurrent product, acquisition, seasonality, or environmental changes were ruled out.
   DISCRIMINATOR: use evidence that separates redesign exposure from calendar time, or document and test the relevant identifying assumptions for an eligible design.

Contract implications:
- Do not mark composition stability as assessed until the diagnostic is actually performed.
- Do not treat either foil as proof that the redesign had no effect.
- The foil exercise does not change the contract verdict; validate the declared fields with claim-contract.

Residual uncertainty:
- The supplied evidence cannot distinguish the causal claim from the retained foils.
```

## Why there are only two foils

The skill defaults to the strongest materially distinct rivals, not a fixed quota. The contract declares the metric definition locked, so this example does not invent a metric-definition failure merely to produce a third foil. A generated foil should earn its place by being compatible with the supplied context and decision-relevant.
