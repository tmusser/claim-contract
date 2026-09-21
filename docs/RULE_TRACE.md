# Rule trace inspection

`claim-contract trace` explains the deterministic path the installed validation profile took
through one submitted contract.

It answers questions such as:

- which rules were mechanically applicable;
- which applicable rules emitted no finding;
- which rules produced the findings behind the final verdict;
- which profile fields each rule declares it consumes;
- which rules were outside the contract's applicable path.

It does **not** add a second validator or a confidence score.

## CLI

```bash
claim-contract trace path/to/contract.yaml
claim-contract trace path/to/contract.yaml --json
```

Text output is intended for debugging and review. JSON output is a versioned
`claim_contract.rule_trace` artifact defined by
[`schemas/rule-trace-v1.schema.json`](../schemas/rule-trace-v1.schema.json).

A successfully produced trace exits `0` even when its embedded validation verdict is
`REVIEW` or `BLOCK`. Trace is an inspection command, not a gate. Malformed or unreadable
input exits `2`.

Use `claim-contract validate` (and optionally `--warnings-as-errors`) when process exit
status should enforce the verdict.

## Rule states

Every rule in the selected profile appears exactly once, in profile-manifest order.

### `TRIGGERED`

The existing validator emitted one or more findings with that rule ID.

The trace embeds those exact findings. It does not reconstruct or paraphrase them.

### `PASS`

The implemented predicate for the rule applied to the contract and emitted no finding.

`PASS` is deliberately narrow. It does **not** mean:

- the declaration is true;
- the evidence is correct;
- the check was performed adequately;
- the statistical method is appropriate;
- the analysis is scientifically valid;
- the claim is safe to publish or use for a decision.

It means only that the applicable implemented rule did not fire on the submitted declarations.

### `NOT_APPLICABLE`

The implemented applicability predicate for the rule did not apply.

For example, a descriptive claim can make comparison-only rules mechanically
`NOT_APPLICABLE`. This does not establish that the analysis has no comparison-related risk
outside the declared contract.

## Example

For a descriptive contract, a trace may include:

```text
CC001 BLOCK PASS
  Consumes: claim.text, claim.type, ...
  Reason: All required fields and basic supported values passed the implemented checks.

CC201 BLOCK NOT_APPLICABLE
  Consumes: claim.type, claim.text, claim.comparison.baseline, claim.comparison.comparison
  Reason: No comparison/causal requirement was detected from claim type or causal-language matching.
```

For a comparison missing uncertainty:

```text
CC203 REVIEW TRIGGERED
  Consumes: claim.type, claim.text, evidence.estimate.value, evidence.uncertainty
  Reason: Rule emitted 1 finding(s).
  Finding: evidence.uncertainty — The estimate has no declared uncertainty information.
```

## Single-source execution boundary

Trace instrumentation lives inside the same validator execution path used by
`validate_contract()`.

`validate_contract_with_trace()` returns the normal validation report plus the internal rule
evaluations from that same run. `validate_contract()` continues to return only the report and
keeps its public verdict behavior unchanged.

Regression tests require, across every shipped contract example, that:

- the trace verdict equals the normal validation verdict;
- the set of `TRIGGERED` rule IDs equals the set of rule IDs in the normal report findings;
- the findings embedded under triggered rules exactly equal the normal validator findings;
- non-triggered entries contain no findings.

That prevents trace from becoming a parallel implementation that can silently disagree with
validation.

## Identity and drift

The machine-readable trace carries:

- the exact parsed-contract SHA-256 binding;
- the semantic profile-manifest SHA-256 binding;
- the profile name and contract version when present.

The trace also embeds the profile manifest's descriptive trigger, consumed fields, severity,
and known boundary for each rule.

These bindings detect content or profile drift. They do not authenticate who produced the
trace, make it tamper-proof, or prove the underlying analysis correct.

## Interpretation boundary

Rule trace is mechanical explainability for the harness.

It does not:

- discover undeclared evidence;
- inspect raw data;
- verify that declared checks were actually performed;
- validate causal assumptions;
- rank rules by importance;
- assign confidence or scientific-validity scores;
- replace qualified analytical review.

A suspicious-looking `READY` trace is useful precisely because it shows which implemented
checks passed and which never applied. It does not turn `READY` into a stronger claim.
