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

## Report binding

New contract-bound validation reports also preserve the semantic identity of the selected profile:

```json
{
  "contract": {
    "profile": "minimum-v0.1",
    "profile_manifest_binding": {
      "algorithm": "sha256",
      "canonicalization": "profile-manifest-semantics-v1",
      "profile_manifest_sha256": "..."
    }
  }
}
```

The digest covers the machine-readable manifest's schema/type, profile metadata, interpretation limits, rule count, and full ordered rule metadata. The top-level `tool` block is deliberately excluded, so a package-version change does not create ruleset drift when the manifest semantics are unchanged.

Changing rule IDs, severities, consumed fields, trigger text, known boundaries, rule order, profile metadata, or profile-wide scope fields changes the digest.

A saved report can compare its bound profile identity with the currently installed manifest through the existing verifier:

```bash
claim-contract report verify report.json --contract contract.yaml
```

Current bound reports report `Profile manifest SHA-256: MATCH` or `MISMATCH`. Historical report-v1 documents that predate this field remain schema-valid and report `Profile manifest SHA-256: UNBOUND`; their existing contract-binding verification semantics are preserved.

The digest is an identity/drift check, not an authenticity mechanism. It does not prove that saved findings were genuinely computed by the bound profile, make a report tamper-proof, or establish scientific validity. A party able to rewrite a report and its digest can construct a new internally consistent artifact.

## Compatibility

The profile manifest schema, validation profile, contract document schema, report schema, and package version are separate versioned concepts.

`profile_manifest_binding` is additive and optional in report-v1 for historical compatibility. Newly generated contract-bound reports include it. A future change to what `profile-manifest-semantics-v1` includes would require a new canonicalization identifier rather than silently changing the existing digest meaning.
