# Portable review packet manifests

A completed review can cross a machine, agent workspace, or project-folder
boundary without losing its sidecars. Use the manifest to inventory the exact
files and verify the copies before trusting the handoff.

## Create and transport

Use a **dedicated packet directory**, not an entire project or repository.
Stage the packet, returned contracts, captured validator JSON, logs, proposals,
and any approved evidence files in that directory. Rewrite supported local inline
links in `packet.md` to point to files inside it. Do not copy confidential or
out-of-scope source material just to make a packet portable.

```bash
claim-contract packet manifest create ./review-001 --json
# Save the returned manifest_sha256 separately in caller-controlled storage.
# Copy the entire directory, including packet-manifest.json.
claim-contract packet manifest verify ./received/review-001 --json
claim-contract packet manifest verify ./received/review-001 \
  --expected-sha256 <caller-retained-digest> --json
```

Creation checks the existing link and validation-summary gates before writing
`packet-manifest.json`. A BLOCK report is allowed if the report and table
accurately represent the declared contract. Creation fails when a supported
local link escapes the packet or points at an unbundled file. External HTTP(S)
and mail links are left as references, not downloaded or verified.

The manifest records:

- schema/type, producer tool version, entrypoint and interpretation boundary;
- every regular file under the packet directory, by relative POSIX path and
  SHA-256 of its exact bytes, excluding only the manifest itself;
- each returned contract's corresponding validator report path, parsed-contract
  input binding, and the profile-manifest binding recorded in that report.

No absolute source paths, timestamps, or filesystem-dependent metadata are
added to the manifest. Empty directories are not inventoried. The manifest
does not authenticate the original baseline; keep the baseline and its
comparison outside the receiver's control.

Creation refuses to overwrite an existing manifest. Finalize all files first,
then create it **once**. Keep receipt/check output outside the packet directory
after creation (redirecting stdout to a new file inside it would change the
inventory). For a revised packet, retain the original and create a new
directory/version instead of regenerating the old manifest to hide drift.

## Verify at the destination

Verification is read-only. It reports missing, modified, or extra files with
exact relative paths, and checks contract/report mapping and recorded input
bindings when the file inventory matches. It does not execute the current
validator rules; check `packet verify` separately if a current-profile
comparison is wanted.

Use `--expected-sha256` when the caller has retained the original manifest
digest through a separate trusted channel. Without that argument, a matching
manifest establishes self-consistency only: someone could rewrite artifacts
and recompute the manifest. A digest is not a signature.

Both commands return:

- `0`: creation succeeded or verification matched;
- `1`: packet/manifest integrity or consistency failure;
- `2`: invalid input, unreadable directory/file, or unparseable artifact.

JSON diagnostics include the manifest digest on successful creation or a
completed verification, artifact count, failures, and
`scientific_validation: false`.

## Scope and safety

Only regular files with portable names are allowed; symlinks, special files,
case-insensitive name collisions and `.git` entries are rejected. Stop writers
before snapshotting or verifying; this is not a concurrent filesystem security
boundary. SHA-256 detects byte changes, not the truth of any assertion.

The manifest does not fetch or rewrite evidence, follow external URLs, inspect
arbitrary prose or reference-style links, or check links inside secondary
Markdown files. Such files are still hashed. It does not create a ZIP archive:
copy the dedicated directory with its existing relative layout. It neither
certifies review completeness nor alters READY / REVIEW / BLOCK.

Continue the [caller baseline workflow](REVIEW_BASELINE.md), the
[packet summary check](PACKET_VERIFY.md), and the caller's analytical review.
The portable bundle is a transport and identity layer, not an acceptance gate
for scientific analysis.
