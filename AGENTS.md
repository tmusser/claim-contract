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
- Do not infer sample size, provenance, uncertainty, baseline values, diagnostics, design, the number of comparisons considered, or a multiplicity adjustment from plausible context.
- Do not treat a numeric estimate as proof that qualitative magnitude language is substantively justified.
- Missing evidence must remain missing.
- Do not downgrade a claim type merely to obtain `READY` without showing the user the changed wording and analytical meaning.

## Do not hide REVIEW

A `REVIEW` verdict means human judgment is still required. Do not summarize it as a pass.

## Do not treat BLOCK as automatic falsity

`BLOCK` means the submitted claim violates the selected minimum contract. It does not prove the claim is false. The contract may be incomplete or conservative.

## Preserve the machine-readable envelope

When returning machine-readable results to another agent, preserve:

- `schema_version` and `type`;
- `tool` and `contract` metadata;
- `verdict`, `profile`, and `claim_text` for reports;
- `scientific_validation` (which is always `false`);
- `scope_notice`;
- `not_evaluated`;
- `summary` and every non-PASS finding;
- the structured `error` object for error envelopes.

Do not strip these fields to save tokens. Do not construct a replacement “compact” object that omits the interpretation boundary.

Consumers should accept additive fields within the same schema major version and ignore fields they do not recognize. See [docs/MACHINE_READABLE.md](docs/MACHINE_READABLE.md).

The [`agent_misuse`](examples/adversarial/agent_misuse/) fixture contrasts an unsafe summary with a compliant one. The unsafe version is not an alternate style; it is an example of semantic corruption during handoff.

## No automatic claim laundering

Do not rewrite a blocked causal or magnitude claim into a softer sentence and present it as approved without rerunning the contract on the revised claim.

## Claim-foil boundary

The optional [`claim-foil`](skills/claim-foil/SKILL.md) skill is an upstream adversarial reasoning step, not another validator.

When using it:

- keep `OBSERVED`, `FOIL`, `UNKNOWN`, and `DISCRIMINATOR` visibly distinct;
- treat every foil as a hypothesis until supplied evidence bears on it;
- do not convert an unresolved foil into a claim that the original assertion is false;
- do not mark a contract field complete merely because the skill named a useful discriminator;
- do not let `claim-foil` emit or reinterpret `READY`, `REVIEW`, or `BLOCK`;
- run the deterministic contract normally after the foil pass if a contract verdict is needed.

See [`skills/claim-foil/EXAMPLE.md`](skills/claim-foil/EXAMPLE.md) for a worked example against the existing onboarding conversion fixture.

## Open claim ledger

The repository-level [`claims/ledger.yaml`](claims/ledger.yaml) is a separate evidence backlog for product and research claims that have not been earned yet.

When adjudicating a ledger entry:

- use only the recorded scope, frozen `support_if` / `refute_if` conditions, and referenced evidence;
- do not infer missing benchmark results, labels, sample sizes, model settings, or other evidence;
- use `SUPPORT_MET` / `REFUTE_MET` only for the recorded scoped condition, never as synonyms for “proven,” “true,” or “false”;
- use `INCONCLUSIVE` when evaluated evidence meets neither frozen condition cleanly;
- leave the claim `OPEN` when required evidence has not actually been evaluated;
- record exact evidence references and judge provenance when changing status;
- create a new claim ID if the claim or judge rule changes materially after evidence has been observed rather than moving the goalposts in place.

See [docs/CLAIM_LEDGER.md](docs/CLAIM_LEDGER.md) for the full workflow.
