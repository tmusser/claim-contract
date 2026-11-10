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
| `PACKET_DIR` | New directory inside the calling Claude project's persistent files |
| `TASK_FILE` | Caller-written assignment defining the claims and authorized review scope |

Keep both read-only input trees outside `PACKET_DIR`. Use a fresh packet directory
for each attempt so a failed run cannot leave old validator output looking current.
The caller should install claim-contract's dependencies in the child's Python
environment before launch.

## Local Codex CLI launch

The following Bash recipe assumes the paths are visible on the same filesystem.
Replace the four assignments with caller-selected paths. The caller must first
write the actual review assignment to `TASK_FILE`.

```bash
set -euo pipefail

TOOL_REPO="/absolute/path/to/read-only/claim-contract"
REVIEW_SOURCE="/absolute/path/to/read-only/review-source"
PACKET_DIR="/absolute/path/to/calling-project/reviews/review-001"
TASK_FILE="/absolute/path/to/calling-project/review-task.txt"

test -f "$TOOL_REPO/AGENTS.md"
test -d "$REVIEW_SOURCE"
test -s "$TASK_FILE"
mkdir -p "$(dirname "$PACKET_DIR")"
mkdir "$PACKET_DIR"

{
  printf 'TOOL_REPO=%s\nREVIEW_SOURCE=%s\nPACKET_DIR=%s\n' \
    "$TOOL_REPO" "$REVIEW_SOURCE" "$PACKET_DIR"
  cat <<'TASK'
Read TOOL_REPO/AGENTS.md first, especially Do not invent evidence,
Claim-implicit boundary, and Packet link boundary. These instructions apply
even though the tool checkout is outside your current directory.

Use the absolute path values above when setting shell variables in your commands.
Read the caller assignment below and inspect only the supplied review inputs.
Before authoring, confirm those inputs are readable and create then remove a
write probe in PACKET_DIR. If access fails, report the blocked path and stop.

Write the final review directly to PACKET_DIR/packet.md.
Put declared review contracts in PACKET_DIR/contracts/.
Run the actual validator for each declared contract. Save its stdout directly,
without rewriting it, in PACKET_DIR/validate/ under the corresponding contract
name with a .json suffix. Keep stderr and exit status separately. Exit 1 can
be a completed BLOCK verdict. Exit 2 is an input error and must be resolved or
reported as incomplete. Never substitute a hand-written validator result.

Use relative inline links from packet.md to contracts/ and validate/.
Include only files actually written. Preserve missing evidence as missing.
Keep candidate unstated propositions distinct from adopted contract claims.
Include exactly this sentence in packet.md:
Link integrity only. This does not validate any claim, contract, or evidence.

Run the packet link check against PACKET_DIR/packet.md after all files are
written. Return the absolute packet path, the files created, the executed
checks and exit statuses, and any unresolved errors. A task is complete only
when its files exist at the final destination and its link check exits 0.

Caller assignment follows.
TASK
  cat "$TASK_FILE"
} | codex exec \
  --cd "$PACKET_DIR" \
  --sandbox workspace-write \
  --skip-git-repo-check \
  -c 'approval_policy="never"' \
  -c 'sandbox_workspace_write.writable_roots=[]' \
  -
```

Codex's working directory is the persistent output directory. The tool checkout
and review inputs remain readable from their absolute paths. Keep any external
read-only mounts in force when launching the child.

The launcher requests no additional writable directories. Check the local Codex
configuration and runtime permissions before relying on its sandbox as an
isolation guarantee. The supplied read-only checkout must remain read-only in the
child's actual environment.

See the official [CLI reference](https://learn.chatgpt.com/docs/developer-commands)
and [sandbox guidance](https://learn.chatgpt.com/docs/agent-approvals-security)
for working-directory and filesystem permission behavior.

## Validator invocation inside the child

Run from `PACKET_DIR`, using the supplied tool source. Substitute only contract
names that this review actually created.

```bash
export PYTHONPATH="$TOOL_REPO/src"
mkdir -p validate

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
read-only and the packet directory read-write.

A temporary child workspace without that mapping cannot deliver permanent files
to the caller's project. Report the missing mapping before starting packet
authoring so the caller can configure it.

## Caller completion check

After the child exits, the caller opens `packet.md` at the destination it chose,
checks that all expected contract and validator files exist, and reruns
`claim-contract packet check /absolute/path/to/packet.md --json` there.
Retain partial files for diagnosis when a run fails and use a fresh directory
for a retry. Report incomplete output explicitly.

Link integrity only. This does not validate any claim, contract, or evidence.
