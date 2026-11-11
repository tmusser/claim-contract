# Reviewing against a retained contract baseline

The caller retains the supplied contracts before delegating a review. The reviewer
returns those declarations intact and puts suggested revisions in separate
proposal files. Each proposed field change needs a reason, a source locator, and
an explicit acceptance decision before it becomes an active declaration.

## Retain the inputs

Choose two or three claims for an initial review. Include different concerns,
such as a denominator definition, a comparison, and wording or coverage.

1. Save the exact supplied source text with its locator and revision or file hash.
2. Copy the supplied contracts into a caller-controlled baseline directory. Keep
   claim text, type, population, metric definitions, checks, and unknown fields
   as supplied. If the inputs are only prose, first record verbatim claims and
   explicitly supplied declarations. Leave inferred fields absent and have the
   caller establish that initial baseline before delegation.
3. Give the child read-only access to the baseline directory, outside its writable
   packet directory. Keep a caller-retained inventory of contract names so an
   omitted or extra returned contract is visible.
4. Record the actual source revision, baseline revision or hashes, validator
   revision, tool version, and profile in the review log. If a checkout is dirty
   or has no revision, retain the relevant snapshot or file hashes and say so.

The caller should retain the baseline, packet, proposals, raw validator reports,
and review log in the review project's version history or persistent artifact
store. A local Git commit retains history even when no remote is configured.
Record the validator's separate revision explicitly.

## Run a deterministic preflight

Run the existing validator on the baseline before launching a broad review. Save
the emitted JSON, stderr, and exit status using the
[packet output capture recipe](PACKET_DELEGATION.md#validator-invocation-inside-the-child).
Use `trace` when the applicability of a finding needs explanation.

```bash
claim-contract trace baseline/C01.yaml --json > preflight-C01-trace.json
```

A trace exits zero when inspection completes, including for a BLOCK contract.
Read its findings and preserve its scope notice.

When many contracts share the same findings, summarize the affected claim IDs,
rule IDs, field paths, and counts in the packet. Use the actual declarations and
findings to distinguish these cases.

| Review item | What to record |
| --- | --- |
| Missing declaration | The applicable finding and the missing or blank field |
| Declared failed check or incompatible declaration | The supplied value and the exact finding it triggers |
| Observed analytical issue | The source locator, executed inspection or calculation, result, and remaining uncertainty |

These are explanatory packet groupings. Retain every original finding and the
actual declared-minimum-contract verdict. A rule's `consumed_fields` list alone
does not establish that every listed field is required for every claim.
Uniform BLOCK results should not be turned into a ranking of analytical quality.

Use the shared gaps to narrow the next assignment. Ask for the specific missing
inputs and review the selected claims before expanding the run. Record actual
token usage when available, otherwise record it as unknown. Review changed claims
and claims affected by changed sources or rules on subsequent passes.

## Preserve the useful inspections

For each selected claim, retain a compact record of these checks.

- Compare the quoted claim with its source text verbatim, including qualifiers.
  Record the source locator and any exact wording difference.
- Inspect the metric label, numerator, denominator, population, and unit against
  the supplied definition and calculation. Retain the executed calculation when
  one is available. Keep unresolved definitions unknown.
- Inventory relevant source sentences that no declared claim covers. Preserve
  unstated propositions as candidates under the claim-implicit boundary.

Attribute each finding to its actual origin, such as validator output, reviewer
inspection, an executed calculation, or caller review. Report a calculated
denominator error separately from a missing denominator declaration.

## Detect drift before accepting the packet

Compare every returned contract against the caller-retained baseline. Compare
the inventories as well so missing or extra files cannot bypass a per-file check.
Run from the packet directory, with `BASELINE_DIR` pointing to the protected
baseline. The following name is synthetic.

```bash
mkdir -p diffs
claim-contract contract diff "$BASELINE_DIR/C01.yaml" contracts/C01.yaml \
  --fail-on-change --json > diffs/C01-returned.json
```

Exit zero means the parsed declarations match. Exit one means at least one field
changed, even if both contracts still produce BLOCK. Exit two means the comparison
could not complete. The JSON diff is emitted on exit one so the caller can inspect
every detected change.

Stop acceptance on any unexpected change or inventory mismatch. Keep the original
baseline intact and recover the returned contract from it. Put intended changes
in `proposed/` and compare those separately.

```bash
claim-contract contract diff "$BASELINE_DIR/C01.yaml" proposed/C01.yaml \
  --json > diffs/C01-proposed.json
```

A successful comparison with the default options exits zero even when fields
differ. Proposal diffs preview the declared-contract verdict transition.

## Proposal and acceptance record

Use one row per changed field in a proposal note. Preserve the full machine
diff alongside it so removals, additions, missing values, and explicit nulls remain
inspectable.

| Field path | Baseline value or MISSING | Proposed value or MISSING | Reason | Source locator or UNKNOWN | Decision |
| --- | --- | --- | --- | --- | --- |

The caller checks that every changed field has a row. A type reclassification
must explain how the analytical meaning changes and which findings disappear.
A population addition must cite an explicit declaration or remain a proposal.
A check set to true must point to supplied evidence or an executed check.

Record the user's explicit acceptance, rejection, or deferral with a locator
to the decision and the exact proposed version. The reviewer cannot approve its
own changes. A matching link, a reason, or a more favorable verdict does not
establish acceptance.

After acceptance, the caller retains a new baseline version, reruns validation,
and records the relationship to the original baseline and proposal. Preserve the
original reports. Unknown evidence remains unknown until actually supplied or
checked.

## Completion boundary

The caller checks the inventory, returned-contract diffs, proposal records, report
bindings, and packet links at the persistent destination. Use
`claim-contract report verify` for saved report-to-contract binding checks.
The changed-contract exit gate detects drift. The caller enforces proposal
coverage and acceptance decisions.

A review is useful when it catches a supported issue or makes an unresolved
question actionable. A READY result describes only the declared minimum contract.
Link integrity only. This does not validate any claim, contract, or evidence.
