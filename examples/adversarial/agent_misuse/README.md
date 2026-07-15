# Agent misuse: READY is not approval

The contract in this directory receives `READY`. The adversarial behavior happens afterward, when an agent overstates that verdict.

Compare:

- [`unsafe_summary.md`](unsafe_summary.md) converts `READY` into scientific approval and permission to publish.
- [`safe_summary.md`](safe_summary.md) preserves the declared-contract boundary and need for human review.

Expected contract result:

```text
Verdict: READY
Findings: none
Scientific validation: false
```

Run:

```bash
claim-contract validate examples/adversarial/agent_misuse/contract.yaml --json
```

The validator cannot control downstream prose. Agents must preserve `scientific_validation`, `scope_notice`, `not_evaluated`, and all findings rather than reducing the report to the verdict alone.
