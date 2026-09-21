# Evidence receipts

Evidence receipts are an optional sidecar for retaining **where a declared evidence field is
supported**, without changing the analytical contract or pretending to verify the underlying
analysis.

They address a narrow gap in the original claim-contract model: the validator can check a
declaration such as `missingness_assessed: true`, but the declaration itself may still be
unsupported or invented.

A receipt makes that support trail inspectable.

It does not make it true.

## Sidecar

A v1 sidecar is bound to one exact parsed contract and one Git revision:

```yaml
schema_version: "1.0"
type: claim_contract.evidence_receipts
scientific_validation: false
automatic_verification: false
scope_notice: >-
  These receipts record retained repository references only and do not verify
  that the referenced material proves or adequately supports a declaration.

contract:
  input_binding:
    algorithm: sha256
    canonicalization: parsed-contract-v1
    contract_sha256: "<exact contract binding>"

snapshot:
  repository_revision: "<full 40-character commit sha>"

receipts:
  - field: evidence.checks.metric_definition_locked
    refs:
      - artifacts/metric-definition-review.md

  - field: evidence.checks.missingness_assessed
    refs:
      - artifacts/missingness-report.json
    note: "Retained output from the analyst's missingness review."
```

The schema is published at
[`schemas/evidence-receipts-v1.schema.json`](../schemas/evidence-receipts-v1.schema.json).

## Inspect

```bash
claim-contract receipts inspect contract.yaml receipts.yaml
claim-contract receipts inspect contract.yaml receipts.yaml --json
```

Inspection checks two different things and keeps them separate.

### Receipt integrity

Integrity checks are mechanical:

- the sidecar's parsed-contract SHA-256 matches the supplied contract;
- the pinned Git revision resolves locally;
- each ref is a safe repository-relative path;
- each ref exists at the pinned revision.

Broken integrity exits `1`.

Malformed input exits `2`.

### Receipt coverage

Coverage is informational and never changes the contract verdict.

The inspector uses the deterministic rule trace to identify declared `evidence.*` fields
consumed by rules that were mechanically applicable (`PASS` or `TRIGGERED`). Fields that
are missing/null/empty are not receipt targets because the contract has no declaration there
to support.

Aggregate mappings such as `evidence.checks` are omitted when more specific consumed fields
beneath them are already targets.

Each target is reported as:

- `RECEIPTED` — the sidecar contains one or more refs for that field;
- `UNRECEIPTED` — no receipt is recorded for that applicable declaration.

A valid sidecar with unreceipted fields still exits `0`. This is deliberate: receipt
completeness is not a new validation rule.

Receipts for declared evidence fields that are not on the current applicable rule path are
preserved as `unused_receipts`.

## Machine-readable inspection

JSON output uses
`claim_contract.evidence_receipt_inspection` schema v1:

[`schemas/evidence-receipt-inspection-v1.schema.json`](../schemas/evidence-receipt-inspection-v1.schema.json).

The envelope explicitly carries:

- `scientific_validation: false`;
- `automatic_verification: false`;
- `changes_validation_verdict: false`;
- saved/current contract bindings and their match state;
- the semantic profile-manifest binding used to derive the applicable field set;
- pinned-revision/ref resolution results;
- receipt coverage counts and per-field rule IDs.

If the saved contract binding does not match the supplied contract, coverage is not attributed
to the new contract. The inspection reports the binding mismatch and exits `1`.

## Interpretation boundary

`RECEIPTED` means only:

> one or more retained repository refs were declared for this field and, when integrity is
> clean, those refs resolve at the pinned revision.

It does **not** mean:

- the referenced document is relevant;
- the document proves the declaration;
- the computation is correct;
- the check was performed adequately;
- the analyst interpreted it correctly;
- the evidence is scientifically valid;
- the contract should be `READY`.

The inspector never opens or interprets referenced files. It verifies identity/existence only.

This distinction is essential. Otherwise a file path becomes an approval token, recreating
the same false-confidence problem that receipts are meant to expose.

## Relationship to rule trace

Rule trace answers:

> Which implemented rules applied, and which declared fields did they consume?

Evidence receipts answer:

> For the applicable declared evidence fields, which retained repository refs were recorded?

Neither answers:

> Does the underlying evidence actually establish the analytical claim?

That remains outside the deterministic harness.
