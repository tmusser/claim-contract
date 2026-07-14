# Rule reference: minimum-v0.1

| Rule | Severity | Trigger |
| --- | --- | --- |
| CC001 | BLOCK | Required claim or evidence field is missing. |
| CC101 | REVIEW | Metric definition is not declared locked. |
| CC102 | REVIEW | Missingness was not declared assessed. |
| CC201 | BLOCK | A comparison claim lacks baseline/comparison groups. |
| CC202 | BLOCK | Relative or percentage effect lacks a baseline value. |
| CC203 | REVIEW | Comparative or causal estimate lacks uncertainty. |
| CC204 | REVIEW | Observational before/after design lacks a composition-stability check. |
| CC205 | REVIEW | Comparison multiplicity was not assessed, is malformed, or lacks an adjustment/rationale when more than one comparison is declared. |
| CC206 | BLOCK | Qualitative magnitude language lacks a numeric estimate and declared scale. |
| CC301 | BLOCK | Causal claim/language uses an ineligible design. |
| CC302 | BLOCK | Quasi-experimental causal claim lacks documented identifying assumptions. |
| CC303 | BLOCK | Randomized causal claim lacks validated treatment assignment. |
| CC304 | REVIEW | Observational intervention comparison lacks an explicit non-causal caveat. |
| CC305 | REVIEW | Any otherwise eligible causal claim still requires qualified human review in `minimum-v0.1`. |

## CC205 declared multiplicity

For comparison and causal claims, declare:

```yaml
evidence:
  checks:
    multiple_comparisons_assessed: true
  multiplicity:
    comparisons: 12
    adjustment: benjamini_hochberg
    rationale: null
```

When more than one comparison is declared, either `adjustment` or `rationale` must be non-empty. A rationale may document an explicitly exploratory analysis where no confirmatory error-rate claim is made.

The harness cannot detect comparisons that were never declared.

## CC206 magnitude language

Words such as `large`, `substantial`, `material`, `meaningful`, `major`, `small`, `modest`, or `negligible` require both:

```yaml
evidence:
  estimate:
    value: 0.02
    scale: absolute
```

This is a language/evidence consistency check. It does not decide whether `0.02` is substantively large or small in the relevant domain.

These rules test declarations, not the underlying truth of those declarations.
