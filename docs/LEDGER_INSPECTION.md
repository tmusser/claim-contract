# Ledger inspection

The open claim ledger is a durable evidence backlog. `claim-contract` can inspect that recorded state without directly parsing YAML:

```bash
claim-contract ledger list --status OPEN --json
claim-contract ledger show CCL-002 --json
```

Both commands default to `claims/ledger.yaml`. An alternate ledger path may be supplied positionally:

```bash
claim-contract ledger list path/to/ledger.yaml --status OPEN --json
claim-contract ledger show CCL-002 path/to/ledger.yaml --json
```

## Inspection is not adjudication

These commands are deliberately read-only.

They do not:

- evaluate free-text `support_if` or `refute_if` conditions;
- inspect evidence and decide whether a frozen condition was met;
- infer a new status;
- rewrite a claim, scope, judge contract, evidence, judgment, or provenance field;
- mutate the ledger.

The JSON envelope makes that boundary explicit with:

```json
{
  "inspection": {
    "automatic_adjudication": false,
    "mutates_ledger": false,
    "notice": "Inspection exposes recorded ledger fields only. It does not evaluate support_if, refute_if, evidence, or whether any status should change, and it does not mutate the ledger."
  }
}
```

A recorded `SUPPORT_MET`, `REFUTE_MET`, or `INCONCLUSIVE` status is shown as recorded state. The inspection command does not independently verify that judgment.

## `ledger list`

`ledger list` returns recorded claim entries in ledger order. `--status` performs an exact filter on the stored `status` field only.

```bash
claim-contract ledger list --status OPEN
claim-contract ledger list --status OPEN --json
```

Supported recorded statuses are:

- `OPEN`
- `SUPPORT_MET`
- `REFUTE_MET`
- `INCONCLUSIVE`
- `RETIRED`

A filter with no matching claims succeeds with `count: 0` and an empty `claims` array.

The JSON form preserves each selected claim object as recorded in the source ledger rather than constructing a second semantic summary of it.

## `ledger show`

`ledger show` selects one claim ID and returns the recorded claim object:

```bash
claim-contract ledger show CCL-002
claim-contract ledger show CCL-002 --json
```

Human-readable output labels `support_if` and `refute_if` as **recorded, not evaluated**. JSON output preserves the complete recorded `judge_contract` verbatim.

An unknown claim ID is an input error and exits `2`.

## Machine-readable envelope

Successful JSON inspection emits `claim_contract.ledger_inspection` with `schema_version: "1.0"`.

The envelope contains:

- tool name and package version;
- source ledger schema version, type, and scope notice;
- inspection mode (`list` or `show`);
- the recorded-status filter or claim ID, when applicable;
- `automatic_adjudication: false`;
- `mutates_ledger: false`;
- selected recorded claim objects;
- a deterministic count of selected records.

The envelope schema is published at [`schemas/ledger-inspection-v1.schema.json`](../schemas/ledger-inspection-v1.schema.json).

The inspection schema validates the envelope and the stable `id` / `status` surface of embedded records. The full embedded claim records remain governed by the source claim-ledger schema. This keeps inspection forward-compatible with additive ledger fields without silently creating a second ledger specification.

## Exit behavior

| Condition | Exit code |
| --- | ---: |
| successful list/show, including zero matches | `0` |
| missing ledger, unknown claim ID, unsupported status, or malformed ledger input | `2` |

Inspection does not use exit `1` because it does not adjudicate claim quality or evidence status.

## Relationship to provenance verification

Ledger inspection and provenance verification answer different questions:

```bash
claim-contract ledger list --status OPEN --json
claim-contract ledger verify claims/ledger.yaml
```

`ledger list` / `show` expose recorded state. `ledger verify` checks whether commit-pinned repository revisions and context references resolve in the local Git worktree. Neither command judges whether `support_if` or `refute_if` has been satisfied.
