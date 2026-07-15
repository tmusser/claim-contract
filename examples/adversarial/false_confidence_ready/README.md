# False confidence: mechanically READY

This fixture is intentionally uncomfortable.

The contract is complete enough to receive `READY`, but its provenance is an agent-supplied export and the caveat states that neither the raw data nor the declared checks were independently verified.

Expected result:

```text
Verdict: READY
Findings: none
Scientific validation: false
```

The lesson is not that the claim is trustworthy. The lesson is that `claim-contract` evaluates declarations against implemented rules; it does not verify whether those declarations are true.

Run:

```bash
claim-contract validate examples/adversarial/false_confidence_ready/contract.yaml
```

A consumer that summarizes this result as “validated” or “safe to publish” is misusing the verdict.
