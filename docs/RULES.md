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
| CC301 | BLOCK | Causal claim/language uses an ineligible design. |
| CC302 | BLOCK | Quasi-experimental causal claim lacks documented identifying assumptions. |
| CC303 | BLOCK | Randomized causal claim lacks validated treatment assignment. |
| CC304 | REVIEW | Observational intervention comparison lacks an explicit non-causal caveat. |
| CC305 | REVIEW | Any otherwise eligible causal claim still requires qualified human review in `minimum-v0.1`. |

These rules test declarations, not the underlying truth of those declarations.
