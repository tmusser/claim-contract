# Agent instructions

This repository is designed to be callable by AI agents, but agents must preserve its limitations.

## Required interpretation

Always describe a verdict as the status of the **declared minimum contract**.

Use:

> The declared minimum contract is READY under `minimum-v0.1`. This does not validate the underlying science or analysis.

Never translate `READY` into:

- true
- correct
- valid analysis
- proven
- statistically sound
- scientifically sound
- unbiased
- causal
- safe to publish

## Do not invent evidence

- Do not set a check to `true` unless the input or an executed verification step supports it.
- Do not infer sample size, provenance, uncertainty, baseline values, diagnostics, or design from plausible context.
- Missing evidence must remain missing.
- Do not downgrade a claim type merely to obtain `READY` without showing the user the changed wording and analytical meaning.

## Do not hide REVIEW

A `REVIEW` verdict means human judgment is still required. Do not summarize it as a pass.

## Do not treat BLOCK as automatic falsity

`BLOCK` means the submitted claim violates the selected minimum contract. It does not prove the claim is false. The contract may be incomplete or conservative.

## Preserve the scope notice

When returning machine-readable results to another agent, include:

- `verdict`
- `profile`
- `scientific_validation` (which is always `false`)
- `scope_notice`
- `not_evaluated`
- all non-PASS findings

Do not strip these fields to save tokens.

## No automatic claim laundering

Do not rewrite a blocked causal claim into a softer sentence and present it as approved without rerunning the contract on the revised claim.
