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

All machine-readable reports must include:

- `schema_version` and document `type`;
- tool and contract metadata;
- the submitted claim text;
- the selected profile;
- the verdict;
- `scientific_validation: false`;
- the fixed scope notice;
- categories the harness did not evaluate;
- deterministic finding counts;
- non-PASS findings with stable rule IDs.

Machine-readable input errors must retain the same `scientific_validation`, `scope_notice`, and `not_evaluated` fields.

Removing the scope notice or `not_evaluated` list, permitting `scientific_validation: true`, or changing their meaning is a semantic breaking change even if a consumer could still parse the JSON.

See [MACHINE_READABLE.md](MACHINE_READABLE.md) and the versioned schemas in [`schemas/`](../schemas/).
