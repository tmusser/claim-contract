# Machine-readable profile manifest

`claim-contract` exposes the selected validation profile as a versioned machine-readable document:

```bash
claim-contract profile show minimum-v0.1 --json
```

The output type is `claim_contract.profile_manifest` with `schema_version: "1.0"`. Its published schema is [`schemas/profile-manifest-v1.schema.json`](../schemas/profile-manifest-v1.schema.json).

## What the manifest contains

Each rule exposes:

- `id`: stable rule ID such as `CC203`;
- `severity`: `REVIEW` or `BLOCK`;
- `consumed_fields`: declared contract fields read by the rule;
- `trigger`: a short human-readable description of when the rule fires;
- `known_boundary`: what the rule does not establish or inspect.

The top-level manifest also preserves the normal interpretation boundary:

- `scientific_validation: false`;
- the fixed `scope_notice`;
- the `not_evaluated` categories;
- the profile name and canonical input-contract schema path.

## Source-of-truth boundary

The executable validator and the manifest share the same rule registry for rule IDs and severities. Tests also lock the registry against the rule IDs used by the validator and the ID/severity table in [`docs/RULES.md`](RULES.md).

Trigger logic remains executable code in the validator. The manifest's `trigger` text is descriptive documentation of that logic, not a second machine-executable rule language.

Likewise, `consumed_fields` means that a rule reads those declared fields. It does not mean those fields are sufficient to establish analytical correctness, scientific validity, or truth.

## Example

A rule entry looks like:

```json
{
  "id": "CC203",
  "severity": "REVIEW",
  "consumed_fields": [
    "claim.type",
    "claim.text",
    "evidence.estimate.value",
    "evidence.uncertainty"
  ],
  "trigger": "A comparative or causal estimate is present without declared uncertainty information.",
  "known_boundary": "The rule checks that uncertainty is declared, not whether it was computed correctly or is statistically appropriate."
}
```

## Human-readable output

Without `--json`, the same registry is rendered as compact text:

```bash
claim-contract profile show minimum-v0.1
```

This is an inspection command only. It does not load a contract, execute validation, produce a verdict, or change any rule semantics.

## Compatibility

The profile manifest schema, validation profile, contract document schema, report schema, and package version are separate versioned concepts.

A future compatibility or digest feature can build on this manifest, but reports do not carry a profile-manifest digest in this version. Adding such a binding should be treated as a separate compatibility decision rather than silently changing report identity semantics.
