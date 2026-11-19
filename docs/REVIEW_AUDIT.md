# Assigned-work completion audit

The existing packet checks establish link integrity, report consistency, and
(optional) byte identity. None establishes that the receiver accounted for
every caller-requested inspection. The optional `packet audit` command checks
that coverage against the caller's own retained structured assignment and
baseline directory, not the receiver's interpretation of its scope.

## Caller and receiver inputs

Keep the original YAML from [review-task.yaml](../templates/review-task.yaml)
and the baseline contract directory outside the returned packet. The baseline
directory contains only baseline contracts (YAML/JSON) in its inventory.
The receiver preserves the task bytes in `task.md`, returns selected contracts
under `contracts/`, and produces `review-work.json` beside `packet.md`.
The original task and baseline must not reside in the packet.

The checker resolves targeted/delta lists against the caller baseline, or
expands `scope.contracts: all` in full mode. It applies the existing defaults:
all three focus checks if omitted, no questions if omitted. An empty focus
list is valid. It expects one record per selected contract for **each** of
wording, denominator, coverage, and one record per question in its original
order (one-based index). Out-of-scope contracts do not receive records.
The structured task's objective, source locator declaration and delta context
are checked for presence/shape, not source validity. Other task controls are
still caller-reviewed; the audit does not interpret prose instructions,
resolve affected contracts, parse effort targets, or enforce proposal mode.

## Work record format (v1)

```json
{
  "schema_version": "1.0",
  "type": "claim_contract.review_work",
  "work_status": "partial",
  "records": [
    {
      "kind": "focus",
      "contract": "C01.yaml",
      "check": "wording",
      "status": "not_requested",
      "artifact": null,
      "detail": "Outside caller focus."
    },
    {
      "kind": "focus",
      "contract": "C01.yaml",
      "check": "denominator",
      "status": "blocked",
      "artifact": null,
      "detail": "The eligible-user denominator was not supplied."
    },
    {
      "kind": "focus",
      "contract": "C01.yaml",
      "check": "coverage",
      "status": "not_requested",
      "artifact": null,
      "detail": "Outside caller focus."
    },
    {
      "kind": "question",
      "index": 1,
      "question": "What is missing?",
      "status": "completed",
      "artifact": "packet.md",
      "detail": "The eligible-user denominator is missing; see the first answer."
    }
  ]
}
```

This is an illustrative, partial review of one selected contract with
denominator focus and one question. Each record must have exactly the fields
shown for its kind. The `contract` field is the baseline-relative path, not a
display label; the `question` string must match the original exactly.

- `completed`: nonblank result/answer, plus a nonempty regular supporting file
  inside the returned packet. Include a useful section locator in the detail
  when possible. The artifact path itself is an exact relative POSIX path,
  without a fragment. Assignment/work-record/packet-manifest files cannot
  support their own completion. This status records a receiver assertion,
  not a mechanically verified inspection.
- `blocked`: nonblank specific reason and optional existing local artifact,
  or null. Honest blocked work makes the audit incomplete, not scientifically
  invalid.
- `not_requested`: only for the focus checks outside caller scope;
  artifact must be null and detail explains exclusion.

An absent, duplicate, malformed, or scope-incompatible requested record is
reported as not completed. Questions are independent work slots; record the
answer even when the substantive conclusion is that an input is unknown.
Additional checks requested in a question must be described in that question's
answer/artifacts; the audit does not infer subchecks from natural language.

## Run at the destination

```bash
claim-contract packet audit ./review-001 \
  --task ./retained/review-task.yaml \
  --baseline ./retained/contracts --json
```

The JSON report gives expected records and derived statuses, counts, selected
contracts and failures. It flags changed task snapshots, omitted or extra
returned contracts, missing/duplicate/unexpected records, false
`not_requested` labels, altered question text, missing supporting files, and
incompatible overall work status.

- Exit 0: every expected record is accounted for and all requested records
  declare completion with the required artifact and detail.
- Exit 1: incomplete or inconsistent return, including explicitly blocked work.
- Exit 2: caller input is unreadable or cannot establish expected scope.

Derived `complete` means the record audit has no failure; `partial` means at
least one requested record meets the mechanical completion requirements but
another audit requirement failed; `blocked` means no requested record meets
them and an audit requirement failed. A zero-request task can pass with
explicit exclusions and matching inventory. This status does not certify
workflow acceptance.

Continue the retained-baseline diff gate, saved-report verification,
`packet check`, `packet verify`, optional manifest verification and manual
review of the actual analytical answers. File presence is not evidence of
execution or answer quality; a receiver can still write an incorrect answer
into an existing file. No verdict or claim is changed by this audit.
Plain-text assignments retain the existing manual completion workflow. The
audit requires structured YAML; it will not invent scope from prose.
