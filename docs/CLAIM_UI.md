# Claim Map UI

The optional claim map is a read-only React frontend for browsing the repository claim graph and tracing where a recorded claim came from.

It visualizes:

- declared claim-graph roots and edges;
- the recorded ledger claim text, scope, status, and decision impact;
- when the claim was recorded;
- the ledger record reference and frozen creation snapshot;
- repository files already referenced by ledger provenance/evidence;
- optional explicit source-file metadata;
- optional database lineage down to system, database/schema, table, and query reference or query text.

The UI is an inspection surface only. It does **not** validate evidence, run SQL, inspect a database, adjudicate the ledger, or mutate any source file.

## Run locally

From the repository root:

```bash
python -m pip install -e .
claim-contract ui export
cd ui
npm install
npm run dev
```

The exporter writes `ui/public/claim-map.json`. The React app reads that static bundle.

To build a production-static frontend:

```bash
claim-contract ui export
cd ui
npm install
npm run build
```

The compiled app is written to `ui/dist/`.

## Export command

```bash
claim-contract ui export \
  --ledger claims/ledger.yaml \
  --graph claims/graph.yaml \
  --provenance claims/provenance.yaml \
  --out ui/public/claim-map.json
```

All flags have repository defaults. `--provenance` is optional; when omitted, the exporter uses `claims/provenance.yaml` if that file exists.

The exporter combines existing sources rather than creating a new source of truth:

- `claims/ledger.yaml` remains authoritative for claim text, status, `provenance.recorded_at`, record reference, creation snapshot, and evidence refs;
- `claims/graph.yaml` remains authoritative for declared relevance roots/edges;
- `claims/provenance.yaml` is optional enrichment for source files and database/query lineage not already represented cleanly in the ledger.

The generated bundle is versioned as `claim_contract.claim_ui_bundle` schema `1.0`.

## Optional provenance sidecar

The sidecar is intentionally separate from ledger v1.2 so UI lineage does not force a ledger-schema migration or change adjudication semantics.

Example:

```yaml
schema_version: "1.0"
type: claim_contract.claim_provenance
scope_notice: "Claim provenance records declared source and data-lineage metadata only. It does not verify that a file, table, or query supports, proves, or generated the claim."

claims:
  - claim_id: CCL-004
    source_files:
      - ref: analysis/onboarding_effect.md
        role: analysis
        note: Human-reviewed analysis note.

    data_sources:
      - system: athena
        catalog: AwsDataCatalog
        database: analytics
        table: funnel_events
        query:
          ref: queries/onboarding_effect.sql
          sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
        note: Query used to construct the evidence extract.
```

A query may declare:

- `ref`: a repository path, saved-query identifier, or other explicit reference;
- `text`: exact query text;
- `sha256`: an optional digest for identity.

At least `ref` or `text` is required.

The exporter does not open a query ref, execute SQL, discover tables, or infer lineage from query syntax. Those would turn a provenance declaration into an unbounded analyzer.

## What the UI shows automatically

Even with an empty optional sidecar, the UI can show useful provenance already present in the ledger:

- **Logged time** from `provenance.recorded_at`;
- **Record ref** from `provenance.record_ref`;
- **Creation context** from `provenance.context_snapshot.refs`;
- **Origin refs** from `provenance.origin_refs`;
- **Current evidence refs** from `evidence.current_refs`;
- **Judgment evidence refs** when a claim has been adjudicated.

Repeated refs are merged into one file card with multiple provenance roles.

## Data/privacy boundary

The bundle is static JSON shipped to the browser.

If you put raw SQL in `query.text`, that SQL becomes browser-readable. Do not include credentials, secrets, personal data, sensitive literals, or SQL that should not be exposed to UI users.

Use a query `ref` plus optional digest when the exact SQL should remain outside the static UI bundle.

The UI does not fetch arbitrary repository files or database content at runtime.

## Graph semantics

The UI preserves `claims/graph.yaml` semantics:

- graph edges declare relevance only;
- roots are explicit;
- connectivity does not establish support, truth, entailment, priority, or scientific validity;
- a prune candidate is a structural classification, not an instruction to delete a claim.

The browser does not implement a second graph analyzer. The exporter uses the existing claim-graph validation/classification path and serializes the result.

## Schemas

- [`schemas/claim-provenance-v1.schema.json`](../schemas/claim-provenance-v1.schema.json)
- [`schemas/claim-ui-bundle-v1.schema.json`](../schemas/claim-ui-bundle-v1.schema.json)

Both are inspection/provenance contracts. Neither changes `minimum-v0.1` or READY / REVIEW / BLOCK.
