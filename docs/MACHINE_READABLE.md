# Machine-readable interoperability

`claim-contract validate ... --json` emits exactly one JSON validation document to stdout. `claim-contract profile show ... --json` emits exactly one JSON profile-manifest document. `claim-contract handoff chart ...` emits exactly one JSON chart-handoff document. Successful `claim-contract ledger list/show ... --json` commands emit exactly one JSON ledger-inspection document.

The output is designed for agents, CI jobs, and other tools, but machine readability must not erase the interpretation boundary. Validation reports, input-error envelopes, profile manifests, and chart handoffs preserve `scientific_validation: false`, the fixed scope notice, and a non-empty `not_evaluated` list where defined by the schema. Ledger inspections preserve the source ledger scope notice plus an explicit `automatic_adjudication: false` / `mutates_ledger: false` boundary.

Consumers must preserve those fields when forwarding or summarizing a result.

## Output types

Five versioned document types are currently defined:

| Type | Schema | Used for |
| --- | --- | --- |
| `claim_contract.report` | [`schemas/report-v1.schema.json`](../schemas/report-v1.schema.json) | A completed validation with a `READY`, `REVIEW`, or `BLOCK` verdict. |
| `claim_contract.error` | [`schemas/error-v1.schema.json`](../schemas/error-v1.schema.json) | A contract that could not be loaded or validated as input. |
| `claim_contract.profile_manifest` | [`schemas/profile-manifest-v1.schema.json`](../schemas/profile-manifest-v1.schema.json) | Versioned rule metadata for a validation profile. |
| `claim_contract.chart_handoff` | [`schemas/chart-handoff-v1.schema.json`](../schemas/chart-handoff-v1.schema.json) | Strict bounded claim context for downstream chart work. |
| `claim_contract.ledger_inspection` | [`schemas/ledger-inspection-v1.schema.json`](../schemas/ledger-inspection-v1.schema.json) | Read-only recorded claim-ledger state for `list` / `show` inspection. |

All currently use `schema_version: "1.0"`, but each schema family evolves independently.

## Report envelope

```json
{
  "schema_version": "1.0",
  "type": "claim_contract.report",
  "tool": {
    "name": "claim-contract",
    "version": "0.1.0"
  },
  "contract": {
    "version": "0.1",
    "profile": "minimum-v0.1",
    "input_binding": {
      "algorithm": "sha256",
      "canonicalization": "parsed-contract-v1",
      "contract_sha256": "..."
    },
    "profile_manifest_binding": {
      "algorithm": "sha256",
      "canonicalization": "profile-manifest-semantics-v1",
      "profile_manifest_sha256": "..."
    }
  },
  "verdict": "REVIEW",
  "profile": "minimum-v0.1",
  "claim_text": "Seven-day activation differed between cohort A and cohort B.",
  "scientific_validation": false,
  "scope_notice": "The submitted fields were checked against implemented minimum-contract rules. This is not scientific validation.",
  "not_evaluated": [
    "whether the data are accurate, representative, or free of leakage"
  ],
  "summary": {
    "finding_count": 1,
    "review_count": 1,
    "block_count": 0
  },
  "findings": [
    {
      "rule_id": "CC203",
      "severity": "REVIEW",
      "path": "evidence.uncertainty",
      "message": "The estimate has no declared uncertainty information.",
      "action": "Provide an interval, standard error, resampling summary, or explain why uncertainty is out of scope."
    }
  ]
}
```

The existing top-level `profile`, `verdict`, `claim_text`, `scientific_validation`, `scope_notice`, `not_evaluated`, and `findings` fields remain in v1 for backward compatibility.

## Contract input binding

Generated reports are bound to the complete parsed contract content that produced the verdict. The binding uses SHA-256 over a deterministic `parsed-contract-v1` canonicalization.

The canonicalization is semantic rather than byte-for-byte:

- mapping key order does not affect the hash;
- YAML whitespace and formatting do not affect the hash after parsing;
- changing a contract value, adding or removing a declared field, or changing nested evidence changes the hash.

The submitted contract `version`, when present, is also preserved under `contract.version`. The selected profile remains under both `contract.profile` and the existing top-level `profile` field.

Python callers can check an in-memory report before forwarding it:

```python
contract = load_contract("contract.yaml")
report = validate_contract(contract)
assert report.matches_contract(contract)
```

## Profile-manifest binding

New contract-bound reports also fingerprint the semantic machine-readable manifest for the selected profile. The binding uses SHA-256 over `profile-manifest-semantics-v1`.

The digest includes the profile-manifest schema/type, profile metadata, interpretation limits, rule count, and full ordered rule metadata. The top-level manifest `tool` block is excluded so a package-version-only change does not create false ruleset drift.

This means changes to rule IDs, severities, consumed fields, trigger descriptions, known boundaries, rule order, profile metadata, or profile-wide scope fields change the profile digest even when the contract text itself is unchanged.

Python callers can recompute and compare the identity explicitly:

```python
manifest = get_profile_manifest(report.profile)
binding = report.resolved_profile_manifest_binding()
assert binding is not None
assert binding.matches_manifest(manifest.to_dict())
```

The profile binding is a drift detector, not proof that the report findings were authentically computed by that ruleset. It does not sign the report, validate the analysis, or upgrade any verdict.

## Saved report verification

A saved JSON report can be checked later through the CLI:

```bash
claim-contract validate contract.yaml --json > report.json
claim-contract report verify report.json --contract contract.yaml
```

Representative success output for a current report:

```text
Binding: MATCH
Contract SHA-256: MATCH
Saved SHA-256: ...
Current SHA-256: ...
Profile manifest SHA-256: MATCH
Saved profile manifest SHA-256: ...
Current profile manifest SHA-256: ...
Bound contract version: 0.1
Bound profile: minimum-v0.1
```

Exit behavior is intentionally simple:

| Condition | Exit code |
| --- | ---: |
| saved contract binding matches and any present profile binding matches | `0` |
| contract content has drifted | `1` |
| a present profile-manifest binding differs from the currently installed manifest | `1` |
| malformed, unsupported, unreadable, or contract-unbound report/contract | `2` |

Historical report-v1 documents that contain a contract input binding but predate `profile_manifest_binding` retain their previous contract-verification behavior and print `Profile manifest SHA-256: UNBOUND`.

Binding verification is a content-identity check only. It does not authenticate who created the report, make the report tamper-proof, validate the correctness of the analysis, or upgrade `READY` into scientific approval. A party able to rewrite a report and its bindings can construct a new internally consistent artifact; SHA-256 here is a drift detector, not a signature.

The published v1 report schema keeps `contract.version`, `contract.input_binding`, and `contract.profile_manifest_binding` optional so reports created before those fields existed remain valid v1 documents. Newly generated contract-bound reports include both bindings.

## Profile manifest

Agents and tooling can inspect the selected profile without parsing Markdown or source code:

```bash
claim-contract profile show minimum-v0.1 --json
```

The `claim_contract.profile_manifest` document exposes each rule's ID, severity, consumed contract fields, short trigger description, and known boundary. It also preserves the profile-wide interpretation limits and points to the canonical input-contract schema.

Rule IDs and severities are shared with the executable validator through one registry. Trigger text remains descriptive documentation of the executable rule logic; the manifest is not a second rule engine and does not produce a verdict.

See [PROFILE_MANIFEST.md](PROFILE_MANIFEST.md) for the full contract and boundary.

## Chart handoff envelope

A contract can be revalidated and exported as strict downstream context:

```bash
claim-contract handoff chart contract.yaml > chart-handoff.json
```

Representative shape:

```json
{
  "schema_version": "1.0",
  "type": "claim_contract.chart_handoff",
  "tool": {
    "name": "claim-contract",
    "version": "0.1.0"
  },
  "destination": {
    "tool": "chart-contract",
    "purpose": "bounded_claim_context"
  },
  "claim": {
    "text": "Median support-ticket resolution time was 18 hours in June 2026.",
    "metric": {
      "name": "median_resolution_hours",
      "unit": "hours"
    },
    "population": "support tickets closed in June 2026",
    "time_window": "2026-06-01/2026-06-30"
  },
  "evidence_context": {
    "provenance_source": "warehouse.support_tickets",
    "caveats": [
      "Operational summary for the declared population and window only."
    ]
  },
  "validation": {
    "verdict": "READY",
    "profile": "minimum-v0.1",
    "scientific_validation": false,
    "scope_notice": "The submitted fields were checked against implemented minimum-contract rules. This is not scientific validation.",
    "not_evaluated": ["..."],
    "summary": {
      "finding_count": 0,
      "review_count": 0,
      "block_count": 0
    },
    "findings": []
  },
  "contract": {
    "version": "0.1",
    "profile": "minimum-v0.1",
    "input_binding": {
      "algorithm": "sha256",
      "canonicalization": "parsed-contract-v1",
      "contract_sha256": "..."
    }
  }
}
```

The chart handoff is intentionally closed-world. Its v1 schema rejects undeclared chart-design fields rather than treating them as harmless extensions. The exporter does not choose a chart type, mark, encoding, aggregation, axis, scale, normalization, title, annotation, color, or layout.

A `REVIEW` or `BLOCK` handoff may still be emitted so unresolved status cannot be hidden by transport. Process exit status continues to reflect the underlying verdict. Missing transferable contract values remain `null`; they are not guessed.

The embedded contract input binding uses the same `parsed-contract-v1` identity mechanism as reports. Python callers can use `ChartHandoff.matches_contract(...)` before reusing the artifact in memory.

The strict chart-handoff v1 envelope does not currently carry `profile_manifest_binding`. Adding that field is a separate handoff-compatibility decision rather than silently expanding a closed-world schema.

The handoff is a producer-side contract only in this release. It does not automatically invoke or configure `chart-contract`; downstream chart authoring and chart-contract auditing remain independent stages.

See [CHART_HANDOFF.md](CHART_HANDOFF.md) for the full boundary.

## Ledger inspection envelope

Recorded ledger state can be inspected without directly parsing the YAML source:

```bash
claim-contract ledger list --status OPEN --json
claim-contract ledger show CCL-002 --json
```

Representative shape:

```json
{
  "schema_version": "1.0",
  "type": "claim_contract.ledger_inspection",
  "tool": {
    "name": "claim-contract",
    "version": "0.1.0"
  },
  "ledger": {
    "schema_version": "1.1",
    "type": "claim_contract.claim_ledger",
    "scope_notice": "Ledger judgments record whether a frozen evidence condition was met. They are not scientific validation and do not prove a claim universally true or false."
  },
  "inspection": {
    "mode": "list",
    "status_filter": "OPEN",
    "claim_id": null,
    "automatic_adjudication": false,
    "mutates_ledger": false,
    "notice": "Inspection exposes recorded ledger fields only. It does not evaluate support_if, refute_if, evidence, or whether any status should change, and it does not mutate the ledger."
  },
  "count": 1,
  "claims": [
    {
      "id": "CCL-002",
      "status": "OPEN",
      "claim": "...",
      "judge_contract": {
        "support_if": "...",
        "refute_if": "...",
        "otherwise": "INCONCLUSIVE"
      }
    }
  ]
}
```

`ledger list --status ...` performs an exact filter on the recorded `status` field only. `ledger show` selects one recorded claim ID. Neither command evaluates `support_if`, `refute_if`, evidence, or whether a status should change.

Embedded claim objects are preserved from the source ledger rather than rewritten into a new semantic summary. The inspection schema governs the envelope and stable `id` / `status` surface; the full embedded claim record remains governed by the source ledger schema.

Successful inspection exits `0`, including a list filter with zero matches. Missing/malformed ledgers, unsupported statuses, and unknown claim IDs exit `2`. Inspection never uses exit `1` because it does not adjudicate a claim.

See [LEDGER_INSPECTION.md](LEDGER_INSPECTION.md) for the full boundary.

## Error envelope

JSON validation input errors requested with `--json`, and chart-handoff export errors, are written as one JSON document to stdout and exit with code `2`:

```json
{
  "schema_version": "1.0",
  "type": "claim_contract.error",
  "tool": {
    "name": "claim-contract",
    "version": "0.1.0"
  },
  "error": {
    "code": "INPUT_ERROR",
    "message": "Input error: Contract file not found: missing.yaml"
  },
  "scientific_validation": false,
  "scope_notice": "The submitted fields were checked against implemented minimum-contract rules. This is not scientific validation.",
  "not_evaluated": [
    "whether the data are accurate, representative, or free of leakage"
  ]
}
```

Human-readable validation input errors continue to use stderr. Ledger-inspection input errors also use stderr and exit `2`; the contract-oriented `claim_contract.error` envelope is not reused for ledger semantics.

## Compatibility policy

Within schema major version `1`:

- required interpretation fields will not be removed or weakened;
- existing field meanings will not be silently changed;
- new optional fields may be added where the relevant schema permits them;
- rule IDs remain governed by the selected profile, not by the report schema version.

The chart-handoff v1 schema intentionally sets `additionalProperties: false` across its bounded envelope. New handoff content therefore requires an explicit schema compatibility decision rather than silent additive drift.

The ledger-inspection v1 envelope is strict, while embedded claim objects permit source-ledger fields beyond `id` / `status`. This lets inspection preserve additive claim-ledger fields without creating a second ledger schema.

A change that removes `scientific_validation`, `scope_notice`, or `not_evaluated`, permits `scientific_validation: true`, or changes their meaning requires an appropriate new schema major version and is treated as a semantic breaking change.

The package version, report schema version, profile-manifest schema version, chart-handoff schema version, ledger-inspection schema version, contract document version, and rule profile are separate concepts:

- package version: implementation release;
- report schema version: validation-envelope compatibility;
- profile-manifest schema version: rule-metadata envelope compatibility;
- chart-handoff schema version: downstream-context compatibility;
- ledger-inspection schema version: read-only ledger-inspection compatibility;
- contract document version: submitted contract-format identifier, preserved when declared;
- profile: implemented validation-rule semantics.

Report v1 now carries two independent optional identity bindings: `parsed-contract-v1` for the submitted contract and `profile-manifest-semantics-v1` for the selected profile manifest. Their canonicalization identifiers are versioned separately so either identity contract can evolve without silently redefining the other.

## Exit codes

JSON output does not replace process status:

| Condition | Exit code |
| --- | ---: |
| `READY` validation/handoff | `0` |
| `REVIEW` validation/handoff | `0` |
| `REVIEW --warnings-as-errors` | `1` |
| `BLOCK` validation/handoff | `1` |
| report verify match / legacy profile-unbound contract match | `0` |
| report verify contract or bound-profile drift | `1` |
| malformed/unsupported report binding | `2` |
| profile show success | `0` |
| ledger list/show success | `0` |
| unsupported profile | `2` |
| ledger inspection input error | `2` |
| input/export error | `2` |

Consumers should inspect both the JSON `type`/`verdict` when applicable and the process exit code.

## Validation

The test suite validates every example report against `report-v1.schema.json`, validates structured input errors against `error-v1.schema.json`, validates the profile manifest against `profile-manifest-v1.schema.json`, validates bounded chart handoffs against `chart-handoff-v1.schema.json`, validates ledger inspections against `ledger-inspection-v1.schema.json`, locks the manifest against executable and documented rule IDs/severities, verifies generated contract and profile-manifest bindings plus legacy v1 compatibility, verifies ledger inspection returns recorded claims without mutation or automatic adjudication, and verifies that interpretation boundaries remain present.
