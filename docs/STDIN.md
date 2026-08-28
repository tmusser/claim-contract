# Contract input from stdin

Any CLI argument that expects a **claim-contract contract** may use `-` to read the contract from standard input.

```bash
cat contract.yaml | claim-contract validate -
cat contract.yaml | claim-contract validate - --json
cat contract.yaml | claim-contract handoff chart -
cat contract.yaml | claim-contract report verify report.json --contract -
```

Standard input is parsed as YAML; JSON works too because JSON is valid YAML syntax. No filename extension is required.

Using stdin does not change validation semantics or output contracts:

- `READY`, `REVIEW`, and `BLOCK` keep their existing meanings;
- `--warnings-as-errors` keeps the same exit behavior;
- `--json` still emits the same `claim_contract.report` or `claim_contract.error` envelope;
- chart handoff still emits the same bounded `claim_contract.chart_handoff` envelope;
- contract bindings are computed from the parsed contract content exactly as they are for file inputs.

Only contract inputs use `-`. Saved reports and claim-ledger files remain explicit file paths.
