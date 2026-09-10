# Bound assumptions ledger

This synthetic example shows why a structured assumptions ledger carries more information than the current `identifying_assumptions_documented: true` contract flag.

The companion quasi-experimental contract documents its identifying assumptions and therefore does not trigger `CC302`. It still receives `REVIEW` via `CC305`, because every otherwise eligible causal claim requires qualified human review under `minimum-v0.1`.

The sidecar [`ledger.yaml`](ledger.yaml) then preserves two distinct assumption states:

- `continuity_at_cutoff` is `REVIEWED` with an explicit caveat;
- `no_precise_cutoff_manipulation` is `CHALLENGED` because the synthetic density diagnostic contains an unresolved warning sign.

The challenge does not automatically mutate the contract or create a new claim-contract finding. The ledger is a reviewable assumptions artifact, not a second validator.

See [`docs/ASSUMPTIONS_LEDGER.md`](../../docs/ASSUMPTIONS_LEDGER.md) for lifecycle and identity semantics.
