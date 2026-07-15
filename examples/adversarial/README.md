# Adversarial fixtures

These fixtures test where `claim-contract` can create false confidence or be misused. They are not demonstrations of scientific validation.

| Fixture | Expected verdict | Expected findings | Adversarial lesson |
| --- | --- | --- | --- |
| [`false_confidence_ready`](false_confidence_ready/) | `READY` | none | Complete declarations can still be unverified or wrong. |
| [`undeclared_assumptions`](undeclared_assumptions/) | `BLOCK` | `CC302`, `CC305` | A quasi-experimental estimate does not support causal language when identifying assumptions are undocumented. |
| [`agent_misuse`](agent_misuse/) | `READY` | none | A downstream agent can misuse `READY` by translating contract status into scientific approval. |

Run the contracts:

```bash
claim-contract validate examples/adversarial/false_confidence_ready/contract.yaml
claim-contract validate examples/adversarial/undeclared_assumptions/contract.yaml
claim-contract validate examples/adversarial/agent_misuse/contract.yaml --json
```

The expected results are locked by `tests/test_adversarial_examples.py`.

## Interpretation rule

A fixture that returns `READY` is not a positive scientific example. In this directory, `READY` often demonstrates precisely why the scope notice and `not_evaluated` fields must survive downstream handoffs.
