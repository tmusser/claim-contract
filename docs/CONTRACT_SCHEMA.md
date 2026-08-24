# Input contract JSON Schema

`claim-contract` publishes a Draft 2020-12 JSON Schema for the canonical `minimum-v0.1` input document:

- [`schemas/contract-minimum-v0.1.schema.json`](../schemas/contract-minimum-v0.1.schema.json)

The schema gives editors, agents, CI jobs, and other tooling a machine-readable description of the contract shape without changing normal `claim-contract validate` behavior.

## What the schema checks

The schema describes:

- contract document version `0.1` and profile `minimum-v0.1`;
- required claim scope fields;
- metric name, unit, and definition;
- evidence design, positive numeric sample size, provenance source, and checks container;
- primitive types for known estimate, uncertainty, multiplicity, check, and caveat fields;
- optional comparison and rule-specific evidence fields.

Additional properties are allowed. The schema defines the minimum published shape rather than forbidding additive metadata that a workflow may want to preserve.

## What the schema does not check

Schema validity is not a `READY` verdict and is not scientific validation.

The schema deliberately does not encode conditional evidence-to-language rules such as:

- whether a comparison needs explicit groups (`CC201`);
- whether a relative effect needs a baseline value (`CC202`);
- whether uncertainty is required (`CC203`);
- whether multiplicity handling is adequate (`CC205`);
- whether causal language is eligible for the declared design (`CC301`-`CC305`).

Those remain deterministic profile rules in `claim-contract validate`.

This separation is intentional. A contract can be structurally valid and still receive `REVIEW` or `BLOCK`.

## Validation behavior is unchanged

`claim-contract validate` does **not** run JSON Schema validation before the rule engine.

That preserves existing verdict semantics. For example, if `claim.population` is missing, ordinary validation still emits `BLOCK CC001` instead of converting the omission into a parser/schema input error.

Likewise, fields whose absence is intentionally handled by `REVIEW` rules are not promoted into unconditional schema requirements. A missing `evidence.checks.metric_definition_locked`, for example, can remain structurally valid and is handled by `CC101`.

## Tooling example

The repository already uses `jsonschema` as a development dependency. A consumer can validate a parsed YAML contract directly:

```python
import json
from pathlib import Path

import jsonschema
import yaml

schema = json.loads(
    Path("schemas/contract-minimum-v0.1.schema.json").read_text(encoding="utf-8")
)
contract = yaml.safe_load(Path("contract.yaml").read_text(encoding="utf-8"))

jsonschema.Draft202012Validator(schema).validate(contract)
```

Run `claim-contract validate contract.yaml` separately when a `READY`, `REVIEW`, or `BLOCK` contract verdict is needed.

## Compatibility boundary

The contract document version, validation profile, report schema version, and package version are separate concepts.

Publishing this schema does not make the input format closed-world. Additive metadata remains allowed, and future profile or document-format changes should receive their own versioned schema rather than silently changing the meaning of this file.
