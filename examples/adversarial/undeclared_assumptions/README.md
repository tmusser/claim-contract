# Undeclared assumptions: causal BLOCK

This fixture supplies a quasi-experimental estimate, uncertainty interval, provenance, comparison groups, and multiplicity declaration. It still leaves the identifying assumptions undocumented.

Expected result:

```text
Verdict: BLOCK
Findings: CC302, CC305
```

- `CC302` blocks the claim because the required identifying assumptions were not declared documented.
- `CC305` preserves qualified human review for every otherwise eligible causal claim under `minimum-v0.1`.

Run:

```bash
claim-contract validate examples/adversarial/undeclared_assumptions/contract.yaml
```

The harness does not determine whether assumptions such as parallel trends, exclusion restrictions, or no interference actually hold. It only checks the submitted declaration.
