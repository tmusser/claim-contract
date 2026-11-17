# Packet validation-summary consistency

The optional `claim-contract packet verify packet.md` command checks a **restricted,
explicitly marked summary table** against returned contracts and the raw validator
JSON saved beside them. It complements, but does not replace,
`claim-contract packet check packet.md` (links and JSON syntax).

Use it when a delegated agent might summarize a BLOCK report as READY, alter
claim wording, omit a finding, point to the wrong report, or quietly drop a
contract from the returned inventory. It does not parse or make assertions about
free-form prose elsewhere in the review.

## Required packet layout

```text
PACKET_DIR/
  packet.md
  contracts/
    C01.yaml
    C02.yaml
  validate/
    C01.json
    C02.json
    C01.stderr
    C01.exit-code
```

Subdirectories under `contracts/` and `validate/` are supported if the relative
stem stays identical (for example, `contracts/team/C01.yml` corresponds to
`validate/team/C01.json`). All selected returned contracts and all JSON report
files under these directories need exactly one summary row.

Include exactly one second-level heading `## Validation summary` and this
five-column Markdown table, with one data row per returned contract:

```md
## Validation summary

| Contract | Claim text | Verdict | Findings | Report |
| --- | --- | --- | --- | --- |
| [C01](contracts/C01.yaml) | The redesign improved activation. | BLOCK | CC301/BLOCK/claim.text; CC203/REVIEW/evidence.uncertainty | [JSON](validate/C01.json) |
| [C02](contracts/C02.yaml) | Eligible-user activation was 27%. | READY | - | [JSON](validate/C02.json) |
```

The text above is *illustrative*, not a report from the bundled fixtures.

- **Contract / Report:** ordinary inline Markdown links, relative to `packet.md`.
  No URLs, filesystem-absolute paths, query strings, fragments, or paths
  escaping the required directories. Spaces may be percent encoded.
- **Claim text:** exact `claim.text` including punctuation/case. Escape literal
  pipe characters as `\|`. Do not add Markdown emphasis, code markup, truncation,
  ellipses, or an invented paraphrase.
- **Verdict:** the literal `READY`, `REVIEW`, or `BLOCK` from the saved report.
  These are minimum-contract verdicts, not scientific judgments.
- **Findings:** `-` for none, otherwise **all** saved findings as
  `RULE_ID/SEVERITY/path` tokens separated by semicolons. Order is flexible;
  duplicates are counted. For example:
  `CC203/REVIEW/evidence.uncertainty; CC301/BLOCK/claim.text`.
  An operator summary may highlight fewer findings elsewhere, but this table
  cannot silently omit them.

## CLI and exit behavior

```bash
claim-contract packet check /path/to/packet.md --json
claim-contract packet verify /path/to/packet.md --json
```

- `0` — every row matches its returned artifacts and every contract/report is
  represented exactly once.
- `1` — consistency failure (bad table, missing/duplicate row, missing artifact,
  mismatched verbatim claim, verdict or finding, stale/tampered JSON, wrong path).
- `2` — the requested packet file itself cannot be read.

JSON output uses `claim_contract.packet_consistency_check` schema version `1.0`,
includes `rows_checked` and line-numbered `failures` (`line`, `code`, `target`,
`reason`), and states `scientific_validation: false` and
`automatic_adjudication: false`. For a missing packet it returns an `error`
envelope rather than silent success.

## How the checks work

1. Parse exactly the declared validation table. Fail closed when it is absent,
   malformed, or ambiguous.
2. Resolve relative links *inside* `contracts/` and `validate/`, including
   symlink resolution. Match each contract to a report with the same relative
   stem and `.json` suffix.
3. Load the declared contract and captured validator report. Re-run the
   installed deterministic `minimum-v0.1` validator on the contract, comparing
   the saved contract/profile bindings, verdict, full findings, scope limits,
   summary counts, and other report semantics. `tool.version` is intentionally
   excluded; a profile/rule semantic change can still invalidate a saved report.
   JSON comparisons preserve booleans versus integers.
4. Compare the literal packet claim/verdict/finding tokens with the actual
   contract and saved report; enumerate any extra or unlisted returned
   contracts/JSON reports.

## Boundaries

This does **not** authenticate saved validator stdout, inspect original data,
confirm a declaration is true, assess analytical quality, adjudicate a ledger
claim, or compare the returned contracts with the caller-retained baseline.
Re-running the deterministic validator checks current rule behavior only and
may flag drift when a historical ruleset is no longer installed; preserve the
original profile and revision when a historical comparison matters.

Continue to run the separate caller-retained `contract diff --fail-on-change`
and `report verify` checks, and manually inspect operator questions, source
locators, proposals, and work completion. The summary table is a **mechanical
handoff contract**, not an agent-authored account of what actually happened in
the scientific analysis. Other packet prose remains outside this checker.
