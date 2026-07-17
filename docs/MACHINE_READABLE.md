# Machine-readable interoperability

`claim-contract validate ... --json` emits exactly one JSON document to stdout.

The output is designed for agents, CI jobs, and other tools, but machine readability must not erase the interpretation boundary. Both successful reports and input-error envelopes require:

- `scientific_validation: false`;
- the fixed `scope_notice`;
- a non-empty `not_evaluated` list.

Consumers must preserve those fields when forwarding or summarizing a result.

## Output types

Two versioned document types are currently defined:

| Type | Schema | Used for |
| --- | --- | --- |
| `claim_contract.report` | [`schemas/report-v1.schema.json`](../schemas/report-v1.schema.json) | A completed validation with a `READY`, `REVIEW`, or `BLOCK` verdict. |
| `claim_contract.error` | [`schemas/error-v1.schema.json`](../schemas/error-v1.schema.json) | A contract that could not be loaded or validated as input. |

Both use `schema_version: "1.0"`.

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
    "profile": "minimum-v0.1"
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

## Error envelope

Input errors requested with `--json` are also written as one JSON document to stdout and exit with code `2`:

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

Human-readable input errors continue to use stderr.

## Compatibility policy

Within schema major version `1`:

- required interpretation fields will not be removed or weakened;
- existing field meanings will not be silently changed;
- new optional fields may be added;
- consumers should ignore unknown fields;
- rule IDs remain governed by the selected profile, not by the report schema version.

A change that removes `scientific_validation`, `scope_notice`, or `not_evaluated`, permits `scientific_validation: true`, or changes their meaning requires a new schema major version and is treated as a semantic breaking change.

The package version, report schema version, and rule profile are separate concepts:

- package version: implementation release;
- report schema version: JSON envelope compatibility;
- profile: implemented validation-rule semantics.

The submitted contract document may carry its own `version`, but v1 report envelopes do not claim to reproduce that field until the validator explicitly preserves it.

## Exit codes

JSON output does not replace process status:

| Condition | Exit code |
| --- | ---: |
| `READY` | `0` |
| `REVIEW` | `0` |
| `REVIEW --warnings-as-errors` | `1` |
| `BLOCK` | `1` |
| input error | `2` |

Consumers should inspect both the JSON `type`/`verdict` and the process exit code.

## Validation

The test suite validates every example report against `report-v1.schema.json`, validates structured input errors against `error-v1.schema.json`, and verifies that stripping the scope notice or setting `scientific_validation` to `true` fails schema validation.
