# claim-contract

[![CI](https://github.com/tmusser/claim-contract/actions/workflows/ci.yml/badge.svg)](https://github.com/tmusser/claim-contract/actions/workflows/ci.yml)

A deterministic Python harness for checking whether **declared evidence** meets a **declared minimum contract** for an analytical claim.

> [!IMPORTANT]
> A `READY` verdict is **not scientific validation**. It does not mean a claim is true, causal, reproducible, unbiased, or suitable for a decision. It means only that the submitted fields satisfied the implemented rules in the selected contract profile.

`claim-contract` is designed for analysts, data scientists, and AI agents that need a narrow pre-publication gate between analytical evidence and claim language.

```text
analysis output + proposed claim
              ↓
        claim-contract
              ↓
 READY / REVIEW / BLOCK + explicit findings
              ↓
       human analytical judgment
```

## Read this first: what this is not

`claim-contract` is not:

- a scientist, statistician, analyst, or peer reviewer;
- a substitute for domain expertise or human judgment;
- proof that the submitted data, code, model, or design is correct;
- an automatic causal-inference engine;
- a hypothesis generator or open-ended EDA tool;
- a model-selection or statistical-test recommender;
- a truth detector;
- a guarantee that a claim is useful, important, ethical, or decision-worthy.

The harness only evaluates the information it receives. A complete YAML file can still describe bad analysis. Incorrect declarations can produce a mechanically clean result.

See [LIMITATIONS.md](LIMITATIONS.md) before using a verdict in an automated workflow.

## What it does

The initial `minimum-v0.1` profile checks a small set of explicit claim/evidence mismatches:

- required claim scope, metric, population, time window, sample size, and provenance;
- relative comparisons without a baseline;
- missing comparison groups;
- causal language paired with non-causal designs;
- randomized claims without validated assignment;
- quasi-experimental claims without documented identifying assumptions;
- observational before/after comparisons without a composition-stability check;
- inferential claims without uncertainty information;
- comparison claims without a declared multiplicity assessment;
- declared multiple comparisons without an adjustment strategy or rationale;
- qualitative magnitude claims without a numeric estimate and scale;
- undeclared missingness or unlocked metric definitions;
- mandatory qualified human review for every causal claim in `minimum-v0.1`.

It produces:

- `READY`: no implemented `REVIEW` or `BLOCK` rule fired;
- `REVIEW`: the declared minimum contract still needs judgment or missing checks;
- `BLOCK`: the submitted claim exceeds or violates the declared evidence contract.

These verdicts describe **contract status**, not scientific validity.

The selected profile can also be inspected without scraping Markdown or Python source:

```bash
claim-contract profile show minimum-v0.1 --json
```

The profile manifest exposes each rule's ID, severity, consumed fields, short trigger, and known boundary. It is inspection metadata, not another validator. See [docs/PROFILE_MANIFEST.md](docs/PROFILE_MANIFEST.md).

Saved profile manifests can be compared mechanically across revisions:

```bash
claim-contract profile diff before-profile.json after-profile.json
claim-contract profile diff before-profile.json after-profile.json --json
```

The diff is aligned to the same `profile-manifest-semantics-v1` identity used by report bindings. It reports profile metadata drift, rule additions/removals, rule-field changes, and rule-order drift, but deliberately does **not** classify changes as breaking, compatible, safe, or scientifically improved. See [docs/PROFILE_DIFF.md](docs/PROFILE_DIFF.md).

A validated contract can also be exported as bounded context for downstream chart work:

```bash
claim-contract handoff chart examples/descriptive_summary/contract.yaml > chart-handoff.json
```

The handoff carries exact claim/scope/provenance/caveat context, the validation verdict and findings, and the bound contract identity. It deliberately contains **no chart recommendation, mark, encoding, aggregation, scale, or visual interpretation**. See [docs/CHART_HANDOFF.md](docs/CHART_HANDOFF.md).

The open claim ledger can be inspected without directly parsing YAML:

```bash
claim-contract ledger list --status OPEN --json
claim-contract ledger show CCL-002 --json
```

These commands expose recorded ledger state only. They do **not** evaluate free-text `support_if` / `refute_if`, infer a status, or mutate the ledger. See [docs/LEDGER_INSPECTION.md](docs/LEDGER_INSPECTION.md).

## Verdict gallery

| Example | Expected verdict | What it demonstrates |
| --- | --- | --- |
| [`descriptive_summary`](examples/descriptive_summary/contract.yaml) | `READY` | A complete descriptive declaration satisfies the implemented minimum rules. |
| [`missing_uncertainty`](examples/missing_uncertainty/) | `REVIEW` | A comparison estimate still needs uncertainty information or an explicit scope decision. |
| [`onboarding_conversion`](examples/onboarding_conversion/) | `BLOCK` | Observational before/after evidence does not support causal language. |

The exact verdicts and rule IDs are locked by tests. See the full [example gallery](examples/README.md).

## Adversarial fixtures

The [`examples/adversarial`](examples/adversarial/) gallery exercises the harness where formal output is easiest to overtrust:

- a mechanically `READY` contract whose declarations were not independently verified;
- a quasi-experimental causal claim with undocumented identifying assumptions;
- an agent that converts `READY` into false scientific approval.

These fixtures are intentionally not product demos. They make the boundaries executable and lock the safe interpretation in tests.

## Install and try it

Requires Python 3.10+.

Install the CLI directly from GitHub:

```bash
python -m pip install "git+https://github.com/tmusser/claim-contract.git"
claim-contract --version
```

If you prefer an isolated CLI environment, `pipx` works too:

```bash
pipx install "git+https://github.com/tmusser/claim-contract.git"
```

To run the bundled examples, clone the repository and install the package without development dependencies:

```bash
git clone https://github.com/tmusser/claim-contract.git
cd claim-contract
python -m pip install .
claim-contract validate examples/onboarding_conversion/contract.yaml
```

Contributor setup and tests are documented in [Development](#development).

Representative output:

```text
Verdict: BLOCK
Profile: minimum-v0.1
Scientific validation: false
Scope: The submitted fields were checked against implemented minimum-contract rules. This is not scientific validation.

BLOCK CC301 claim.text
  Causal language is not eligible under design 'observational_before_after'.
  Action: Use non-causal wording or provide an eligible design and its required diagnostics.

REVIEW CC204 evidence.checks.composition_stability_assessed
  Composition stability was not assessed for an observational before/after comparison.

Not evaluated:
- whether the data are accurate, representative, or free of leakage
- whether the analysis code is correct or reproducible
- whether the model or statistical method is appropriate
- whether causal identifying assumptions are actually true
- whether the claim is useful, material, ethical, or decision-worthy
```

## Contract format

A contract is one YAML or JSON document containing a proposed claim and declared evidence:

```yaml
version: "0.1"
profile: minimum-v0.1

claim:
  text: "The onboarding redesign improved seven-day activation by 8%."
  type: causal
  population: new users
  time_window: "2026-04-01/2026-06-30"
  metric:
    name: seven_day_activation_rate
    unit: proportion
    definition: "Users activated within seven days / eligible new users"
  comparison:
    baseline: pre_launch
    comparison: post_launch

evidence:
  design: observational_before_after
  sample_size: 18420
  estimate:
    value: 0.08
    scale: relative
    baseline_value: 0.25
  uncertainty: null
  provenance:
    source: warehouse.funnel_events
  checks:
    metric_definition_locked: true
    missingness_assessed: true
    composition_stability_assessed: false
    treatment_assignment_validated: false
    identifying_assumptions_documented: false
    multiple_comparisons_assessed: true
  caveats: []
```

The complete runnable example is in [`examples/onboarding_conversion/`](examples/onboarding_conversion/). See [docs/RULES.md](docs/RULES.md) for the human rule reference and declared multiplicity fields.

The canonical structural shape for this profile is published as [`schemas/contract-minimum-v0.1.schema.json`](schemas/contract-minimum-v0.1.schema.json). Schema validity is separate from the `READY` / `REVIEW` / `BLOCK` rule engine: `claim-contract validate` does not turn schema failures into parser errors. See [docs/CONTRACT_SCHEMA.md](docs/CONTRACT_SCHEMA.md) for the boundary and tooling guidance.

## CLI

```bash
claim-contract --version
claim-contract validate path/to/contract.yaml
claim-contract validate path/to/contract.yaml --json
claim-contract validate path/to/contract.yaml --format json
claim-contract validate path/to/contract.yaml --warnings-as-errors
claim-contract handoff chart path/to/contract.yaml
claim-contract handoff chart path/to/contract.yaml --warnings-as-errors
claim-contract profile show minimum-v0.1
claim-contract profile show minimum-v0.1 --json
claim-contract profile diff before-profile.json after-profile.json
claim-contract profile diff before-profile.json after-profile.json --json
claim-contract ledger list --status OPEN
claim-contract ledger list --status OPEN --json
claim-contract ledger show CCL-002
claim-contract ledger show CCL-002 --json
claim-contract ledger verify claims/ledger.yaml
```

`--json` is a shortcut for `--format json` on commands that support formatted output. `handoff chart` is JSON-only because its output is a versioned downstream artifact. `ledger list` / `show` default to `claims/ledger.yaml` and accept an alternate ledger path positionally. `--version` prints the installed package version without requiring a contract file.

Exit behavior for validation and chart handoff uses the same verdict gate:

- `READY` exits `0`.
- `REVIEW` exits `0` by default and `1` with `--warnings-as-errors`.
- `BLOCK` exits `1`.
- malformed or unexportable input exits `2`.

A `REVIEW` or `BLOCK` chart handoff is still emitted when validation completed, so downstream tooling cannot mistake transport for approval.

`profile show` exits `0` for a supported profile and `2` for an unsupported profile. `profile diff` exits `0` for a completed comparison and `2` for malformed or unsupported manifest input. Neither command executes analytical validation or produces a compatibility judgment.

`ledger list` / `show` exit `0` for successful inspection and `2` for ledger-input errors. They never use exit `1` because they do not adjudicate claims. `ledger verify` remains a separate read-only provenance check.

## Machine-readable contract

JSON validation reports use `claim_contract.report`; JSON input failures use `claim_contract.error`; profile inspection uses `claim_contract.profile_manifest`; profile drift inspection uses `claim_contract.profile_diff`; chart handoff uses `claim_contract.chart_handoff`; ledger list/show uses `claim_contract.ledger_inspection`. Each currently has its own schema family at `schema_version: "1.0"`.

Machine-readable validation/profile/handoff documents preserve the interpretation boundary with `scientific_validation: false`, the fixed scope notice, and a non-empty `not_evaluated` list where defined by their schemas. Profile diff additionally carries `automatic_compatibility_classification: false`; ledger inspection preserves the source ledger scope notice and explicitly carries `automatic_adjudication: false` and `mutates_ledger: false`.

Published schemas:

- [`schemas/contract-minimum-v0.1.schema.json`](schemas/contract-minimum-v0.1.schema.json) — canonical input shape for the `minimum-v0.1` profile
- [`schemas/profile-manifest-v1.schema.json`](schemas/profile-manifest-v1.schema.json) — machine-readable profile/rule metadata
- [`schemas/profile-diff-v1.schema.json`](schemas/profile-diff-v1.schema.json) — mechanical drift between saved profile manifests
- [`schemas/chart-handoff-v1.schema.json`](schemas/chart-handoff-v1.schema.json) — strict bounded context for downstream chart work
- [`schemas/ledger-inspection-v1.schema.json`](schemas/ledger-inspection-v1.schema.json) — read-only machine-readable ledger inspection
- [`schemas/report-v1.schema.json`](schemas/report-v1.schema.json)
- [`schemas/error-v1.schema.json`](schemas/error-v1.schema.json)

See [docs/MACHINE_READABLE.md](docs/MACHINE_READABLE.md) for output compatibility guarantees, [docs/PROFILE_DIFF.md](docs/PROFILE_DIFF.md) for profile-drift boundaries, [docs/CHART_HANDOFF.md](docs/CHART_HANDOFF.md) for the cross-tool boundary, [docs/LEDGER_INSPECTION.md](docs/LEDGER_INSPECTION.md) for the ledger inspection boundary, and [docs/PROFILE_MANIFEST.md](docs/PROFILE_MANIFEST.md) for profile-manifest semantics. See [docs/CONTRACT_SCHEMA.md](docs/CONTRACT_SCHEMA.md) for input-schema scope and compatibility.

## Python API

```python
from claim_contract import (
    build_chart_handoff,
    get_profile_manifest,
    load_contract,
    validate_contract,
)

contract = load_contract("examples/onboarding_conversion/contract.yaml")
report = validate_contract(contract)
manifest = get_profile_manifest("minimum-v0.1")
handoff = build_chart_handoff(contract)

print(report.verdict)
print(manifest.rule("CC301").known_boundary)
print(handoff.to_dict()["destination"])
for finding in report.findings:
    print(finding.severity, finding.rule_id, finding.message)
```

## Why no automatic rewrite?

The first release does not rewrite a blocked claim into a supposedly safe one. Rewriting can silently create a different analytical assertion and make the harness look more intelligent than it is.

Instead, findings identify the violated boundary and the required action. The analyst or agent must revise the claim or supply better evidence, then run the contract again.

## Agent usage

Agents must read [AGENTS.md](AGENTS.md). In particular, they must not translate `READY` into words such as “true,” “valid,” “proven,” “scientifically sound,” or “causal.”

A safe agent summary is:

> The declared minimum contract is READY under `minimum-v0.1`. This result does not validate the underlying science or analysis.

### Optional `claim-foil` skill

The repository also ships [`skills/claim-foil/SKILL.md`](skills/claim-foil/SKILL.md), an upstream adversarial reasoning step for proposed analytical claims.

`claim-foil` generates the 1-3 strongest materially distinct rival explanations it can justify exploring from the supplied context, keeps `OBSERVED` evidence separate from generated `FOIL` hypotheses, and requires a concrete `DISCRIMINATOR` for every retained foil. It deliberately does **not** produce a contract verdict or treat a foil as refutation.

See the [worked onboarding example](skills/claim-foil/EXAMPLE.md).

## Relationship to chart-contract

`claim-foil` stress-tests **alternative interpretations before validation**.

`claim-contract` checks **evidence-to-language integrity**.

The bounded chart handoff preserves the exact claim, analytical scope, caveats, validation status, and contract identity that downstream chart work is allowed to inherit.

`chart-contract` then checks **claim-to-visual integrity** on the concrete chart/spec and its data/claim inputs.

```text
analysis
  → claim-foil
  → claim-contract
  → bounded chart handoff
  → chart authoring
  → chart-contract audit
  → human analytical judgment
```

The handoff is not a chart generator or adapter. `chart-contract` still performs its own independent audit, and neither tool replaces analytical judgment.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for possible directions and explicit non-goals. The roadmap is intentionally non-promissory: new rules must earn their place with a concrete failure mode, inspectable inputs, tests, and documented blind spots.

## Development

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m claim_contract.cli validate examples/descriptive_summary/contract.yaml
```

## License

MIT. See [LICENSE](LICENSE).
