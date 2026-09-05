# Historical report profile verification

`claim-contract report verify` can verify a saved report against an explicitly supplied machine-readable profile manifest instead of only the profile currently installed with the CLI.

This is useful when a report was created under an older ruleset and the profile metadata has since drifted.

```bash
claim-contract report verify report.json \
  --contract contract.yaml \
  --profile-manifest frozen-profile.json
```

Create or retain profile snapshots with:

```bash
claim-contract profile show minimum-v0.1 --json > frozen-profile.json
```

## What is verified

A bound report already contains two independent identities:

- `parsed-contract-v1` — the parsed contract that produced the report;
- `profile-manifest-semantics-v1` — the machine-readable profile semantics bound into the report.

Normal verification compares the saved profile binding with the profile currently installed under the report's declared profile name:

```bash
claim-contract report verify report.json --contract contract.yaml
```

When `--profile-manifest` is supplied, the contract check is unchanged, but the profile candidate is loaded from that saved JSON artifact instead of the installed profile registry.

Representative successful historical verification:

```text
Binding: MATCH
Contract SHA-256: MATCH
Saved SHA-256: ...
Current SHA-256: ...
Profile manifest SHA-256: MATCH
Saved profile manifest SHA-256: ...
Supplied profile manifest SHA-256: ...
Supplied profile: minimum-v0.1
Bound contract version: 0.1
Bound profile: minimum-v0.1
```

A valid supplied manifest with different semantic content produces `Profile manifest SHA-256: MISMATCH` and exits `1`. A supplied manifest for a different profile name is also an identity mismatch rather than a parser error; the profile name is part of the bound manifest semantics.

Malformed, unsupported, or unreadable supplied manifests exit `2`.

## Historical boundary

This feature verifies **identity**, not historical execution.

A matching supplied profile manifest means only that its `profile-manifest-semantics-v1` digest matches the digest recorded in the report. It does not prove that:

- those exact rules actually executed when the report was created;
- the saved findings are authentic or tamper-proof;
- the report was produced by a trusted party;
- the underlying analysis was scientifically valid;
- the profile was correct, sufficient, or appropriate for the claim.

The SHA-256 binding remains a drift detector, not a signature or provenance attestation.

## Profile-unbound historical reports

Report-v1 documents created before `profile_manifest_binding` remain contract-verifiable without this option and continue to print:

```text
Profile manifest SHA-256: UNBOUND
```

Passing `--profile-manifest` for such a report is rejected with exit `2`. Supplying a manifest later cannot retroactively establish which profile semantics an unbound report originally used.

## Release metadata

`profile-manifest-semantics-v1` deliberately excludes the top-level manifest `tool` block. A saved manifest whose only difference is the claim-contract package version therefore still matches the same bound profile semantics.

This is the same identity contract used by generated reports and by `claim-contract profile diff`.
