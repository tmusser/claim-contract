# Persisting a delegated review packet

When Claude delegates packet authoring to Codex CLI, the caller chooses the final
output directory before launching the child. Give the child read access to its
inputs and write access to that output directory. Write the Markdown, declared
contracts, and validator output directly into that directory.

The caller owns the destination and permission setup. A path in a prompt does
not grant filesystem access.

## Caller inputs

Supply these absolute paths to the child.

| Input | Purpose |
| --- | --- |
| `TOOL_REPO` | Read-only checkout of claim-contract, including its `AGENTS.md` and Python source |
| `REVIEW_SOURCE` | Read-only source material selected for this review |
| `BASELINE_DIR` | Caller-retained, read-only contracts with an inventory and source revision |
| `PACKET_DIR` | New directory inside the calling Claude project's persistent files |
| `TASK_FILE` | Caller assignment with objective, selected contracts, priorities, effort targets, and output preferences |

Keep all read-only input trees outside `PACKET_DIR`. Use a fresh packet directory
for each attempt so a failed run cannot leave old validator output looking current.
The caller should install claim-contract's dependencies in the child's Python
environment before launch. Follow the [review baseline workflow](REVIEW_BASELINE.md)
to retain supplied declarations and run deterministic preflight. The caller chooses
the scope with the [task controls](REVIEW_TASK.md); two or three claims are a
suggested first pass. Supply the selected inventory and explicit assignment to
the child. Start from [the task template](../templates/review-task.yaml) when useful.

## Local Codex CLI launch

The following Bash recipe assumes the paths are visible on the same filesystem.
Replace the five assignments with caller-selected paths. The caller must first
write the actual review assignment to `TASK_FILE`.

```bash
set -euo pipefail

TOOL_REPO="/absolute/path/to/read-only/claim-contract"
REVIEW_SOURCE="/absolute/path/to/read-only/review-source"
BASELINE_DIR="/absolute/path/to/read-only/review-baseline"
PACKET_DIR="/absolute/path/to/calling-project/reviews/review-001"
TASK_FILE="/absolute/path/to/calling-project/review-task.txt"

test -f "$TOOL_REPO/AGENTS.md"
test -d "$REVIEW_SOURCE"
test -d "$BASELINE_DIR"
test -s "$TASK_FILE"
mkdir -p "$(dirname "$PACKET_DIR")"
mkdir "$PACKET_DIR"
cp "$TASK_FILE" "$PACKET_DIR/task.md"

{
  printf 'TOOL_REPO=%s\nREVIEW_SOURCE=%s\nBASELINE_DIR=%s\nPACKET_DIR=%s\n' \
    "$TOOL_REPO" "$REVIEW_SOURCE" "$BASELINE_DIR" "$PACKET_DIR"
  cat <<'TASK'
Read TOOL_REPO/AGENTS.md first, especially Do not invent evidence,
Review baseline boundary, Claim-implicit boundary, and Packet link boundary.
These instructions apply even though the tool checkout is outside your current directory.
Read TOOL_REPO/docs/REVIEW_BASELINE.md for the proposal and acceptance workflow.
Read TOOL_REPO/docs/REVIEW_TASK.md for caller controls and their defaults.

Use the absolute path values above when setting shell variables in your commands.
Read the caller assignment below and record its effective settings in review-log.md.
Use its objective, selected contract inventory, source scope, prioritized questions,
focus checks, proposal mode, effort targets, missing-input policy, and output detail.
Resolve unspecified optional controls using REVIEW_TASK.md. For missing required
scope, unknown values, or conflicting instructions, return blocked with the issue.
The caller's assignment selects the work; preserve all required integrity checks.
Before authoring, confirm the tool and selected baseline contracts are readable
and create then remove a write probe in PACKET_DIR. If this access fails, report
the blocked path and stop. Apply the missing-input policy to missing analytical
source material; a delta review also requires its prior review and change context.

Write the final review directly to PACKET_DIR/packet.md.
Copy the selected baseline contracts into PACKET_DIR/contracts/ unchanged,
preserving relative paths. Match the selected inventory and report any missing
or extra returned contracts. Record baseline contracts outside scope as unreviewed.
Keep the baseline directory read-only. In suggest mode, put useful candidate
revisions in PACKET_DIR/proposed/. In findings_only mode, report findings and
questions without writing revised contracts.
For every changed field, retain a diff, a reason, a source locator or UNKNOWN,
and a pending acceptance decision. Never adopt your own proposals.
Check each returned contract with contract diff --fail-on-change against
BASELINE_DIR. A changed type, inferred population, or filled check is a proposed
edit even when the top-level verdict is unchanged.
Record actual source and validator revisions or retained hashes in review-log.md.
Attribute findings to validator output, reviewer inspection, executed calculation,
or caller review. Separate shared declaration gaps from observed analytical issues.
Run the actual validator for each returned baseline contract. Save its stdout
directly, without rewriting it, in PACKET_DIR/validate/ under the corresponding contract
name with a .json suffix. Keep stderr and exit status separately. Exit 1 can
be a completed BLOCK verdict. Exit 2 is an input error and must be resolved or
reported as incomplete. Never substitute a hand-written validator result.

Use relative inline links from packet.md to contracts/ and validate/.
Include only files actually written. Preserve missing evidence as missing.
Perform the requested focus checks and answer the caller's prioritized questions.
Record each assigned check as completed or blocked with its source or reason.
Record default checks excluded by the assignment as not_requested.
Honor the missing-input policy and save partial work at effort target boundaries.
Start packet.md with answers to the caller's questions and the remaining unknowns.
Keep all findings in linked artifacts even when the summary is concise.
Label any validation of proposed contracts as a proposal preview.
Keep candidate unstated propositions distinct from adopted contract claims.
Include exactly this sentence in packet.md:
Link integrity only. This does not validate any claim, contract, or evidence.

Run the packet link check against PACKET_DIR/packet.md after all files are
written. Return the absolute packet path, the files created, the executed
checks and exit statuses, and any unresolved errors. Return complete, partial,
or blocked work status separately from validator verdicts. A task is complete
only when all assigned work finishes, its files exist at the final destination,
the selected inventory matches, all returned contracts pass the baseline diff
gate, and its link check exits 0. A link-check pass alone cannot complete the task.
Pending proposals remain proposals for the caller to present for acceptance.

Caller assignment follows.
TASK
  cat "$PACKET_DIR/task.md"
} | codex exec \
  --cd "$PACKET_DIR" \
  --sandbox workspace-write \
  --skip-git-repo-check \
  -c 'approval_policy="never"' \
  -c 'sandbox_workspace_write.writable_roots=[]' \
  -
```

Codex's working directory is the persistent output directory. The tool checkout,
review inputs, and retained baseline remain readable from their absolute paths.
Keep external read-only mounts in force when launching the child.

The launcher requests no additional writable directories. Check the local Codex
configuration and runtime permissions before relying on its sandbox as an
isolation guarantee. The supplied read-only checkout must remain read-only in the
child's actual environment.

See the official [CLI reference](https://learn.chatgpt.com/docs/developer-commands)
and [sandbox guidance](https://learn.chatgpt.com/docs/agent-approvals-security)
for working-directory and filesystem permission behavior.

## Validator invocation inside the child

Run from `PACKET_DIR`, using the supplied tool source. Substitute only contract
names from the selected baseline inventory. Run the baseline diff gate for each
returned contract before capturing its validator output.

```bash
export PYTHONPATH="$TOOL_REPO/src"
mkdir -p validate diffs

python -m claim_contract contract diff "$BASELINE_DIR/C01.yaml" contracts/C01.yaml \
  --fail-on-change --json > diffs/C01-returned.json || exit "$?"

if python -m claim_contract validate contracts/C01.yaml --json \
  > validate/C01.json 2> validate/C01.stderr; then
  validation_code=0
else
  validation_code=$?
fi
printf '%s\n' "$validation_code" > validate/C01.exit-code

python -m claim_contract packet check packet.md --json > link-check.json
```

The `C01` name is a synthetic naming example. A validator output file establishes
what the executed command emitted. A link-check pass establishes only link
resolution and linked JSON syntax. Preserve the validator's scope notice and
each actual verdict when writing the packet.

## Isolated child environments

If the child runs in a container or remote workspace, the caller must map
`PACKET_DIR` to persistent storage in the calling project before launch. Supply
the child-visible absolute path in its assignment and retain the corresponding
caller-visible path for the handoff. Mount the tool checkout and review source
and the retained baseline read-only and the packet directory read-write.

A temporary child workspace without that mapping cannot deliver permanent files
to the caller's project. Report the missing mapping before starting packet
authoring so the caller can configure it.

## Caller completion check

After the child exits, the caller opens `packet.md` at the destination it chose,
checks the returned contract inventory against its selected baseline inventory, and runs
`contract diff --fail-on-change` for each returned contract. Inspect every
proposal's diff, reason, source, and decision record. Verify saved report bindings
with `report verify` and rerun
`claim-contract packet check /absolute/path/to/packet.md --json` there.
Compare the packet's `task.md` with the caller-retained assignment, then compare
its effective task settings and work-status table with that assignment. Verify answers to the assigned questions and account for blocked or
not-requested inspections. Retain partial files for diagnosis when a run fails and use a fresh directory
for a retry. Report incomplete output explicitly. The caller presents pending
proposals for explicit acceptance and retains accepted changes as a new baseline
version. The original baseline and reports remain available in the review history.

Link integrity only. This does not validate any claim, contract, or evidence.
