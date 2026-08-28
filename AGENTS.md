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

## Input schema boundary

The published [`minimum-v0.1` input schema](schemas/contract-minimum-v0.1.schema.json) checks canonical document structure and primitive field types. It is not a substitute for `claim-contract validate`.

- Do not translate schema conformance into `READY`.
- Do not treat a schema-valid causal or comparative contract as evidence that the claim is supported.
- Do not skip the deterministic rule engine after a schema check when a contract verdict is needed.
- Preserve missing rule-level evidence as missing; do not fill fields merely to satisfy a schema or obtain a cleaner verdict.

See [docs/CONTRACT_SCHEMA.md](docs/CONTRACT_SCHEMA.md) for the structural-versus-rule boundary.

## Profile manifest boundary

Use this command when an agent needs to inspect the active rule contract without scraping Markdown or source code:

```bash
claim-contract profile show minimum-v0.1 --json
```

The profile manifest is descriptive metadata, not a verdict and not a second validator.

- `consumed_fields` means the rule reads those declared fields; it does not mean those fields are sufficient to establish analytical correctness.
- `trigger` is a concise description of executable rule logic, not a machine-executable replacement for that logic.
- `known_boundary` describes what the rule does not establish; do not omit or reverse that limitation when summarizing the rule.
- Do not fill missing contract fields merely because the manifest says a rule consumes them.
- Do not translate a rule list, rule severity, or manifest-schema match into scientific approval.

See [docs/PROFILE_MANIFEST.md](docs/PROFILE_MANIFEST.md).

## Chart handoff boundary

Use the bounded chart handoff only to preserve declared claim context across the `claim-contract` → `chart-contract` boundary:

```bash
claim-contract handoff chart contract.yaml > chart-handoff.json
```

The handoff is not a chart recommendation and not an approval artifact.

- Preserve the exact `claim.text`; do not soften or rewrite it merely because chart authoring would be easier.
- Preserve population, time window, metric/unit, provenance source, caveats, validation verdict, and every finding.
- Preserve the contract input binding; do not detach the handoff from the contract that produced it.
- Do not add chart type, mark, encoding, aggregation, scale, normalization, or visual-style recommendations to the v1 handoff.
- A `REVIEW` or `BLOCK` handoff remains unresolved downstream; transport does not upgrade it.
- `claim-contract READY` does not imply that any particular visualization is safe or accurate.
- `chart-contract` must still audit the concrete chart/spec independently.

The handoff schema is intentionally closed-world. See [docs/CHART_HANDOFF.md](docs/CHART_HANDOFF.md).

## Preserve the machine-readable envelope

When returning machine-readable results to another agent, preserve:

- `schema_version` and `type`;
- `tool` and `contract` metadata, including `contract.version` and `contract.input_binding` when present;
- `verdict`, `profile`, and `claim_text` for reports;
- `scientific_validation` (which is always `false`);
- `scope_notice`;
- `not_evaluated`;
- `summary` and every non-PASS finding;
- the structured `error` object for error envelopes;
- profile metadata, `rule_count`, and complete `rules` entries when forwarding a profile manifest;
- destination, claim, evidence context, validation, and contract metadata when forwarding a chart handoff;
- source-ledger metadata, inspection metadata, and complete recorded claim objects when forwarding a ledger inspection.

Do not strip these fields to save tokens. Do not construct a replacement “compact” object that omits the interpretation boundary.

Before reusing a saved bound report beside a contract, run:

```bash
claim-contract report verify report.json --contract contract.yaml
```

A matching binding proves only that the parsed contract content matches the input that produced the saved report. It does not authenticate the report, prove the analysis is correct, or upgrade the verdict.

Consumers should accept additive fields within the same schema major version where the relevant schema permits them. The chart-handoff v1 schema is intentionally strict and does not permit undeclared additions. See [docs/MACHINE_READABLE.md](docs/MACHINE_READABLE.md).

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

Agents may inspect recorded ledger state without directly parsing YAML:

```bash
claim-contract ledger list --status OPEN --json
claim-contract ledger show CCL-002 --json
```

These are inspection commands, not adjudication commands.

- Treat `status` as recorded state only; do not claim the inspection command independently verified it.
- Do not evaluate free-text `support_if` or `refute_if` conditions merely because they are exposed in JSON.
- Preserve `automatic_adjudication: false`, `mutates_ledger: false`, and the inspection notice when forwarding the envelope.
- `ledger list --status ...` filters the recorded `status` field only; it does not derive a status from evidence.
- `ledger show` returns the recorded claim entry; it does not decide whether the claim should change state.
- Use `ledger verify` separately when commit-pinned provenance references need to be checked. Provenance verification still does not adjudicate the judge contract.

See [docs/LEDGER_INSPECTION.md](docs/LEDGER_INSPECTION.md) for the inspection contract.

When adding or adjudicating a ledger entry:

- use only the recorded scope, frozen `support_if` / `refute_if` conditions, and referenced evidence;
- preserve the claim's creation provenance separately from later evidence and judgment;
- do not invent a historical `generated_at`; use `null` when the true generation time was not retained;
- resolve repository-relative `context_snapshot.refs` at the pinned `repository_revision`, not at today's `main`;
- do not rewrite creation provenance to match later evidence or repository state;
- do not infer missing benchmark results, labels, sample sizes, model settings, or other evidence;
- use `SUPPORT_MET` / `REFUTE_MET` only for the recorded scoped condition, never as synonyms for “proven,” “true,” or “false”;
- use `INCONCLUSIVE` when evaluated evidence meets neither frozen condition cleanly;
- leave the claim `OPEN` when required evidence has not actually been evaluated;
- record exact evidence references and judge provenance when changing status;
- create a new claim ID if the claim or judge rule changes materially after evidence has been observed rather than moving the goalposts in place.

See [docs/CLAIM_LEDGER.md](docs/CLAIM_LEDGER.md) for the full workflow.
