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

The package version, report schema version, contract document version, and rule profile are separate concepts:

- package version: implementation release;
- report schema version: JSON envelope compatibility;
- contract document version: submitted contract-format identifier, preserved when declared;
- profile: implemented validation-rule semantics.

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

The test suite validates every example report against `report-v1.schema.json`, validates structured input errors against `error-v1.schema.json`, verifies generated contract bindings and legacy unbound v1 compatibility, and verifies that stripping the scope notice or setting `scientific_validation` to `true` fails schema validation.
