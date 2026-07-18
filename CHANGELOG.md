# Changelog

## [Unreleased]

### Added

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

### Changed

- Added a CI badge and compact verdict gallery to the README.
- Expanded limitations and agent guidance for the blind spots of multiplicity and magnitude checks.
- Updated CI to exercise the `--json` alias.
- Linked the adversarial gallery from the README, examples index, limitations, agent instructions, and roadmap.
- Strengthened agent handoff requirements for machine-readable output.
- Documented machine-readable compatibility and semantic-breaking-change rules.
- Hardened CI with read-only permissions, disabled checkout credentials, pip caching, concurrency cancellation, job timeouts, and a complete Python 3.10-3.13 matrix.
- Made pytest fail closed on unknown configuration, undeclared markers, and unexpected `xfail` passes.

## [0.1.0] - 2026-07-12

### Added

- `minimum-v0.1` declared claim/evidence contract.
- Deterministic `READY`, `REVIEW`, and `BLOCK` verdicts.
- Fixed scope notice and explicit `not_evaluated` categories in every report.
- CLI, Python API, examples, tests, CI, MIT license, and agent instructions.
