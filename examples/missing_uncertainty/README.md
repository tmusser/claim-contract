# REVIEW: missing uncertainty

This fixture is intentionally complete enough to avoid `BLOCK`, but it leaves `evidence.uncertainty` undeclared.

Expected result:

```text
Verdict: REVIEW

REVIEW CC203 evidence.uncertainty
  The estimate has no declared uncertainty information.
```

Run:

```bash
claim-contract validate examples/missing_uncertainty/contract.yaml
```

The verdict does not mean the comparison is invalid. It means the declared minimum contract still needs uncertainty information or a documented reason that uncertainty is out of scope.
