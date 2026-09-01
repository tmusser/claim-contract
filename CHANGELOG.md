# Changelog

## [Unreleased]

### Added

- `claim-contract contract diff <before> <after>` with text and `--json` output for mechanical parsed-contract field diffs plus `READY | REVIEW | BLOCK` verdict transitions.
- Versioned `claim_contract.contract_diff` output and `schemas/contract-diff-v1.schema.json`, preserving missing-vs-null state and explicit non-interpretation/scientific-validation boundaries.
- Deterministic `profile-manifest-semantics-v1` SHA-256 bindings from new contract-bound reports to the semantic machine-readable profile manifest used by the report.
- Saved-report verification of present profile-manifest bindings, with explicit `MATCH` / `MISMATCH` / legacy `UNBOUND` output and preserved contract-verification behavior for historical report-v1 artifacts.
- `claim-contract ledger list [ledger] --status <STATUS> --json` and `claim-contract ledger show <CLAIM_ID> [ledger] --json` for read-only machine-readable ledger inspection without automatic adjudication.
- Versioned `claim_contract.ledger_inspection` output with an explicit `automatic_adjudication: false` / `mutates_ledger: false` boundary and published `schemas/ledger-inspection-v1.schema.json`.
- `-` as a first-class stdin contract source for validation and other contract-taking CLI paths, preserving existing verdict, JSON/error-envelope, and exit-code semantics.
- `claim-contract handoff chart <contract>` for emitting a strict JSON-only `claim_contract.chart_handoff` artifact targeted at `chart-contract`.
- Published `schemas/chart-handoff-v1.schema.json` covering exact claim text, metric/unit, population, time window, provenance source, caveats, validation status/findings, and the bound contract identity while explicitly excluding chart-design recommendations.
- Python `ChartHandoff` / `build_chart_handoff(...)` support plus schema, drift, blocked-claim, missing-field, and CLI exit-policy tests.
- `claim-contract profile show minimum-v0.1` with `--json` / `--format json` output for machine-readable profile inspection.
- Versioned `claim_contract.profile_manifest` documents with rule IDs, severities, consumed fields, short triggers, known boundaries, and preserved interpretation limits.
- Published `schemas/profile-manifest-v1.schema.json` plus drift tests that lock manifest IDs/severities against the executable validator and human rule table.
- Published `schemas/contract-minimum-v0.1.schema.json` as the Draft 2020-12 structural contract for canonical `minimum-v0.1` inputs.
- Contract-schema tests that validate every shipped contract, reject malformed structural fields, and lock the boundary between schema validity and `READY` / `REVIEW` / `BLOCK` rule semantics.
- Deterministic SHA-256 bindings from validation reports to the exact parsed contract content that produced them.
- `Report.matches_contract(...)` and `claim-contract report verify` for checking in-memory and saved reports against the contract being shared.
- Preservation of submitted contract `version` metadata inside generated machine-readable reports.
- `claim-contract ledger verify` for read-only resolution of commit-pinned claim-ledger context references against local Git history.
- Claim-ledger schema `1.1` with required creation provenance: generation time when known, durable record time, origin references, and a commit-pinned context snapshot.
- Backfilled provenance for CCL-001 through CCL-003 using the commit that first recorded the ledger while leaving unknown conversational generation timestamps explicitly `null`.
- CI coverage that validates provenance structure, RFC 3339 timestamps, pinned repository revisions, and continued publication of the legacy `1.0` ledger schema.
- Optional `claim-foil` skill for bounded adversarial stress-testing before deterministic contract validation.
- Worked `claim-foil` example that separates observed evidence, rival explanations, unknowns, and discriminating evidence.
- Repository test coverage that locks the skill's non-verdict and missing-evidence safety boundaries.
- Isolated `REVIEW` example for missing uncertainty.
- Executable `READY` / `REVIEW` / `BLOCK` example gallery.
- Parametrized tests that lock example verdicts and exact rule IDs.
- CI coverage for all three verdict paths and `--warnings-as-errors` behavior.
- `CC205` multiplicity assessment and handling checks for comparison claims.
- `CC206` effect-estimate requirement for qualitative magnitude claims.
- `--json` CLI shortcut for agent and tool-calling workflows.
- Non-promissory `ROADMAP.md` with explicit feature promotion gates and non-goals.
- Tests for multiplicity assessment, adjustment/rationale handling, magnitude language, and the JSON alias.
- Adversarial fixtures for false confidence, undeclared identifying assumptions, and downstream agent misuse.
- Tests that lock adversarial verdicts, rule IDs, and safe/unsafe agent-summary boundaries.
- Versioned `claim_contract.report` and `claim_contract.error` JSON envelopes.
- Published report and error JSON Schemas.
- Deterministic finding-count summaries and structured JSON input errors.
- Schema tests covering every example report and mandatory scope fields.
- A package-build CI job that builds both distributions, checks metadata, installs the wheel in isolation, and smoke-tests the installed CLI.
- A standard `claim-contract --version` command backed by the same package metadata used in JSON reports.

### Changed

- Rule severities now come from the same registry used to emit profile manifests, while executable trigger logic and verdict semantics remain unchanged.
- Documented input-schema validation as a separate structural tooling layer; normal `claim-contract validate` continues to emit the existing rule verdicts rather than converting schema mismatches into parser errors.
- Generated v1 report envelopes now carry additive contract and profile-manifest identity metadata while the published v1 schema keeps those fields optional for legacy report compatibility.
- The live claim ledger now uses schema `1.1`; the original `claim-ledger-v1.schema.json` remains published for `1.0` consumers.
- Added a CI badge and compact verdict gallery to the README.
- Expanded limitations and agent guidance for the blind spots of multiplicity and magnitude checks.
- Updated CI to exercise the `--json` alias.
- Linked the adversarial gallery from the README, examples index, limitations, agent instructions, and roadmap.
- Strengthened agent handoff requirements for machine-readable output.
- Documented machine-readable compatibility and semantic-breaking-change rules.
- Hardened CI with read-only permissions, disabled checkout credentials, pip caching, concurrency cancellation, job timeouts, and a complete Python 3.10-3.13 matrix.
- Made pytest fail closed on unknown configuration, undeclared markers, and unexpected `xfail` passes.
- Extended wheel smoke testing to verify the installed CLI version matches package metadata.

## [0.1.0] - 2026-07-12

### Added

- `minimum-v0.1` declared claim/evidence contract.
- Deterministic `READY`, `REVIEW`, and `BLOCK` verdicts.
- Fixed scope notice and explicit `not_evaluated` categories in every report.
- CLI, Python API, examples, tests, CI, MIT license, and agent instructions.
