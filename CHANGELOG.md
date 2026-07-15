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

### Changed

- Added a CI badge and compact verdict gallery to the README.
- Expanded limitations and agent guidance for the blind spots of multiplicity and magnitude checks.
- Updated CI to exercise the `--json` alias.
- Linked the adversarial gallery from the README, examples index, limitations, agent instructions, and roadmap.

## [0.1.0] - 2026-07-12

### Added

- `minimum-v0.1` declared claim/evidence contract.
- Deterministic `READY`, `REVIEW`, and `BLOCK` verdicts.
- Fixed scope notice and explicit `not_evaluated` categories in every report.
- CLI, Python API, examples, tests, CI, MIT license, and agent instructions.
