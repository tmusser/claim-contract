# Contract semantics

## Verdict lattice

Severity is ordered:

```text
BLOCK > REVIEW > READY
```

- Any `BLOCK` finding produces `BLOCK`.
- Otherwise, any `REVIEW` finding produces `REVIEW`.
- Otherwise, the result is `READY`.

## Scope

The profile name identifies a versioned set of implemented rules. It is not a quality grade.

`minimum-v0.1` is intentionally modest. It checks declared fields for common contradictions and omissions. It does not inspect the underlying analytical execution.

## Stable output requirements

All reports must include:

- the submitted claim text;
- the selected profile;
- the verdict;
- `scientific_validation: false`;
- the fixed scope notice;
- non-PASS findings with stable rule IDs;
- categories the harness did not evaluate.

Removing the scope notice or `not_evaluated` list is considered a breaking change in meaning, even if the JSON schema remains technically compatible.
