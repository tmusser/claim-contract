# Profile manifest diff

`claim-contract profile diff` compares two saved machine-readable profile manifests and reports exact profile/rule metadata drift without deciding whether the change is compatible, breaking, safe, desirable, or scientifically correct.

Create snapshots with `profile show`:

```bash
claim-contract profile show minimum-v0.1 --json > before.json
# after upgrading or checking out another revision:
claim-contract profile show minimum-v0.1 --json > after.json

claim-contract profile diff before.json after.json
claim-contract profile diff before.json after.json --json
```

The command accepts JSON profile-manifest files produced by `claim-contract profile show ... --json`. Successful comparison exits `0`; malformed or unsupported input exits `2`.

## What is compared

The diff is aligned to `profile-manifest-semantics-v1`, the same semantic identity used by report/profile bindings.

It reports:

- profile name, contract-schema, description, scope-notice, and `not_evaluated` changes;
- added and removed rules;
- per-rule changes to `severity`, `consumed_fields`, `trigger`, and `known_boundary`;
- pure ordering changes among rules that exist on both sides;
- before/after semantic profile-manifest SHA-256 bindings;
- whether top-level `tool` metadata changed.

The top-level `tool` block is deliberately excluded from semantic profile identity. A package-version-only change therefore appears as `tool_metadata_changed: true` with `semantic_changed: false`.

The diff implementation contains a fail-closed invariant: if the existing semantic binding changes but none of the surfaced semantic fields changed, comparison raises an internal error rather than silently reporting a clean diff.

## Representative text output

```text
Profile: minimum-v0.1 -> minimum-v0.1
Semantic profile changed: true
Tool metadata changed: false
Automatic compatibility classification: false

Profile fields: none
Rules added: none
Rules removed: none
Rules changed:
  CC203
    severity
      - "REVIEW"
      + "BLOCK"
Rule order changed: false
```

## Machine-readable output

`--json` emits `claim_contract.profile_diff` schema `1.0`, published at [`schemas/profile-diff-v1.schema.json`](../schemas/profile-diff-v1.schema.json).

The envelope carries:

- before/after profile names and semantic bindings;
- `semantic_changed`;
- `tool_metadata_changed`;
- `automatic_compatibility_classification: false`;
- profile-level changes;
- full added/removed rule records;
- per-field changes for rules present on both sides;
- before/after rule order plus an explicit order-change flag;
- a deterministic `change_count`.

Added/removed/changed rules are ordered deterministically by rule ID. Per-rule changed fields use the fixed order `severity`, `consumed_fields`, `trigger`, `known_boundary`.

## Boundary

`profile diff` does **not**:

- decide whether a change is backward-compatible;
- classify a change as breaking, safe, risky, major, or minor;
- infer whether changed metadata matches changed executable validator behavior;
- recommend a migration;
- prove either profile is scientifically valid;
- authenticate or tamper-proof either manifest.

A changed SHA-256 means the bound profile semantics differ under the published canonicalization. The diff explains the machine-observable metadata drift; humans and downstream consumers still decide what that drift means for compatibility and use.
