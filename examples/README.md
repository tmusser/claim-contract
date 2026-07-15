# Examples

The examples form a small executable verdict gallery for `minimum-v0.1`.

| Example | Expected verdict | Expected findings | What it demonstrates |
| --- | --- | --- | --- |
| [`descriptive_summary`](descriptive_summary/contract.yaml) | `READY` | none | A complete descriptive declaration satisfies the implemented minimum rules. |
| [`missing_uncertainty`](missing_uncertainty/) | `REVIEW` | `CC203` | A comparison estimate still needs uncertainty information or an explicit scope decision. |
| [`onboarding_conversion`](onboarding_conversion/) | `BLOCK` | `CC203`, `CC204`, `CC301`, `CC304` | Observational before/after evidence does not support causal language. |

Run all three:

```bash
claim-contract validate examples/descriptive_summary/contract.yaml
claim-contract validate examples/missing_uncertainty/contract.yaml
claim-contract validate examples/onboarding_conversion/contract.yaml
```

These expected verdicts are locked by `tests/test_examples.py`. They describe declared-contract status, not scientific validity.

## Adversarial fixtures

The [`adversarial`](adversarial/) gallery covers three different failure surfaces:

- mechanically `READY` output built from unverified declarations;
- causal language with undeclared quasi-experimental assumptions;
- downstream agent prose that converts `READY` into false scientific approval.

These fixtures are locked by `tests/test_adversarial_examples.py`. A `READY` adversarial fixture is intentionally not evidence that the underlying analysis is sound.
