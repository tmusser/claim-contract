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

## Quickstart

```bash
python -m pip install -e ".[dev]"
claim-contract validate examples/onboarding_conversion/contract.yaml
pytest
```

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

The complete runnable example is in [`examples/onboarding_conversion/`](examples/onboarding_conversion/). See [docs/RULES.md](docs/RULES.md) for the full rule reference and declared multiplicity fields.

## CLI

```bash
claim-contract validate path/to/contract.yaml
claim-contract validate path/to/contract.yaml --json
claim-contract validate path/to/contract.yaml --format json
claim-contract validate path/to/contract.yaml --warnings-as-errors
```

`--json` is a shortcut for `--format json` for agent and tool-calling workflows.

Exit behavior:

- `READY` exits `0`.
- `REVIEW` exits `0` by default and `1` with `--warnings-as-errors`.
- `BLOCK` exits `1`.
- malformed input exits `2`.

Machine-readable reports also set `scientific_validation: false` unconditionally.

Every output format includes the scope notice and the list of categories not evaluated.

## Python API

```python
from claim_contract import load_contract, validate_contract

contract = load_contract("examples/onboarding_conversion/contract.yaml")
report = validate_contract(contract)

print(report.verdict)
print(report.scope_notice)
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

## Relationship to chart-contract

`claim-contract` checks **evidence-to-language integrity**.

`chart-contract` checks **claim-to-visual integrity**.

```text
analysis → claim-contract → bounded claim → chart-contract → audited visual
```

Neither tool replaces analytical judgment.

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
