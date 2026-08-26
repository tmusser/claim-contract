# Machine-readable interoperability

`claim-contract validate ... --json` emits exactly one JSON validation document to stdout. `claim-contract profile show ... --json` emits exactly one JSON profile-manifest document. `claim-contract handoff chart ...` emits exactly one JSON chart-handoff document.

The output is designed for agents, CI jobs, and other tools, but machine readability must not erase the interpretation boundary. Validation reports, input-error envelopes, profile manifests, and chart handoffs preserve `scientific_validation: false`, the fixed scope notice, and a non-empty `not_evaluated` list where defined by the schema.

Consumers must preserve those fields when forwarding or summarizing a result.

## Output types

Four versioned document types are currently defined:

| Type | Schema | Used for |
| --- | --- | --- |
| `claim_contract.report` | [`schemas/report-v1.schema.json`](../schemas/report-v1.schema.json) | A completed validation with a `READY`, `REVIEW`, or `BLOCK` verdict. |
| `claim_contract.error` | [`schemas/error-v1.schema.json`](../schemas/error-v1.schema.json) | A contract that could not be loaded or validated as input. |
| `claim_contract.profile_manifest` | [`schemas/profile-manifest-v1.schema.json`](../schemas/profile-manifest-v1.schema.json) | Versioned rule metadata for a validation profile. |
| `claim_contract.chart_handoff` | [`schemas/chart-handoff-v1.schema.json`](../schemas/chart-handoff-v1.schema.json) | Strict bounded claim context for downstream chart work. |

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

A saved JSON report can be checked later through the CLI:

```bash
claim-contract validate contract.yaml --json > report.json
claim-contract report verify report.json --contract contract.yaml
```

Representative success output:

```text
Binding: MATCH
Contract SHA-256: MATCH
Saved SHA-256: ...
Current SHA-256: ...
Bound contract version: 0.1
Bound profile: minimum-v0.1
```

Exit behavior is intentionally simple:

| Condition | Exit code |
| --- | ---: |
| saved binding matches current contract | `0` |
| contract content has drifted | `1` |
| malformed, unsupported, unreadable, or unbound report/contract | `2` |

Binding verification is a content-identity check only. It does not authenticate who created the report, make the report tamper-proof, validate the correctness of the analysis, or upgrade `READY` into scientific approval. A party able to rewrite both a report and its binding can construct a new internally consistent artifact; SHA-256 here is a drift detector, not a signature.

The published v1 report schema keeps `contract.version` and `contract.input_binding` optional so reports created before this feature remain valid v1 documents. Newly generated reports include the binding.

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

The embedded binding is the same content-identity mechanism used by reports. Python callers can use `ChartHandoff.matches_contract(...)` before reusing the artifact in memory.

The handoff is a producer-side contract only in this release. It does not automatically invoke or configure `chart-contract`; downstream chart authoring and chart-contract auditing remain independent stages.

See [CHART_HANDOFF.md](CHART_HANDOFF.md) for the full boundary.

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

Human-readable validation input errors continue to use stderr.

## Compatibility policy

Within schema major version `1`:

- required interpretation fields will not be removed or weakened;
- existing field meanings will not be silently changed;
- new optional fields may be added where the relevant schema permits them;
- rule IDs remain governed by the selected profile, not by the report schema version.

The chart-handoff v1 schema intentionally sets `additionalProperties: false` across its bounded envelope. New handoff content therefore requires an explicit schema compatibility decision rather than silent additive drift.

A change that removes `scientific_validation`, `scope_notice`, or `not_evaluated`, permits `scientific_validation: true`, or changes their meaning requires an appropriate new schema major version and is treated as a semantic breaking change.

The package version, report schema version, profile-manifest schema version, chart-handoff schema version, contract document version, and rule profile are separate concepts:

- package version: implementation release;
- report schema version: validation-envelope compatibility;
- profile-manifest schema version: rule-metadata envelope compatibility;
- chart-handoff schema version: downstream-context compatibility;
- contract document version: submitted contract-format identifier, preserved when declared;
- profile: implemented validation-rule semantics.

Reports do not currently carry a profile-manifest digest. A future binding or cross-version compatibility feature should make that relationship explicit rather than silently changing report identity semantics.

## Exit codes

JSON output does not replace process status:

| Condition | Exit code |
| --- | ---: |
| `READY` validation/handoff | `0` |
| `REVIEW` validation/handoff | `0` |
| `REVIEW --warnings-as-errors` | `1` |
| `BLOCK` validation/handoff | `1` |
| profile show success | `0` |
| unsupported profile | `2` |
| input/export error | `2` |

Consumers should inspect both the JSON `type`/`verdict` when applicable and the process exit code.

## Validation

The test suite validates every example report against `report-v1.schema.json`, validates structured input errors against `error-v1.schema.json`, validates the profile manifest against `profile-manifest-v1.schema.json`, validates bounded chart handoffs against `chart-handoff-v1.schema.json`, locks the manifest against executable and documented rule IDs/severities, verifies generated contract bindings and legacy unbound v1 compatibility, and verifies that interpretation boundaries remain present.
