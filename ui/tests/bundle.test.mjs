import assert from "node:assert/strict";
import test from "node:test";

import {
  ClaimBundleError,
  parseClaimUiBundle,
} from "../src/bundle.js";

function validBundle() {
  return {
    schema_version: "1.0",
    type: "claim_contract.claim_ui_bundle",
    scientific_validation: false,
    automatic_adjudication: false,
    read_only: true,
    scope_notice:
      "The claim map UI visualizes declared graph, ledger, and provenance metadata only. It does not verify evidence, execute queries, adjudicate claims, or mutate source artifacts.",
    generated_from: {
      ledger: "claims/ledger.yaml",
      graph: "claims/graph.yaml",
      provenance: null,
    },
    graph: {
      scope_notice: "Declared relevance only.",
      roots: ["CCL-001"],
      edges: [
        {
          from: "CCL-002",
          to: "CCL-001",
          rationale: "Narrower claim informs the root.",
        },
      ],
    },
    claims: [
      {
        id: "CCL-001",
        status: "OPEN",
        classification: "ROOT",
        is_root: true,
        claim: "Root claim.",
        scope: "Synthetic scope.",
        decision_impact: "Synthetic decision impact.",
        logged_at: "2026-09-27T20:00:00Z",
        generated_at: null,
        record_ref: "abc123",
        provenance_note: null,
        context_snapshot: {},
        source_files: [
          {
            ref: "analysis/root.md",
            roles: ["current_evidence"],
            note: null,
          },
        ],
        data_sources: [],
        judgment: {},
      },
      {
        id: "CCL-002",
        status: "OPEN",
        classification: "CONNECTED",
        is_root: false,
        claim: "Child claim.",
        scope: "Synthetic scope.",
        decision_impact: "Synthetic decision impact.",
        logged_at: "2026-09-27T20:00:00Z",
        generated_at: null,
        record_ref: "def456",
        provenance_note: null,
        context_snapshot: {},
        source_files: [],
        data_sources: [
          {
            system: "athena",
            database: "analytics",
            table: "events",
            query: {
              ref: "queries/child.sql",
              sha256:
                "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            },
          },
        ],
        judgment: {},
      },
    ],
  };
}

function expectBundleError(fn, fragment) {
  assert.throws(fn, (error) => {
    assert.ok(error instanceof ClaimBundleError);
    assert.match(error.message, new RegExp(fragment));
    return true;
  });
}

test("accepts a structurally coherent v1 bundle", () => {
  const bundle = validBundle();
  assert.equal(parseClaimUiBundle(bundle), bundle);
});

test("rejects safety flags that would overstate UI authority", () => {
  const bundle = validBundle();
  bundle.scientific_validation = true;

  expectBundleError(
    () => parseClaimUiBundle(bundle),
    "scientific_validation",
  );
});

test("rejects duplicate claim IDs", () => {
  const bundle = validBundle();
  bundle.claims[1].id = "CCL-001";
  bundle.claims[1].classification = "ROOT";
  bundle.claims[1].is_root = true;
  bundle.graph.edges = [];

  expectBundleError(() => parseClaimUiBundle(bundle), "duplicate value");
});

test("rejects graph edges to unknown claims", () => {
  const bundle = validBundle();
  bundle.graph.edges[0].from = "CCL-999";

  expectBundleError(
    () => parseClaimUiBundle(bundle),
    "unknown source claim CCL-999",
  );
});

test("rejects claim root flags that disagree with graph roots", () => {
  const bundle = validBundle();
  bundle.claims[0].is_root = false;

  expectBundleError(
    () => parseClaimUiBundle(bundle),
    "must match graph.roots membership",
  );
});

test("rejects malformed database query lineage", () => {
  const bundle = validBundle();
  bundle.claims[1].data_sources[0].query = {};

  expectBundleError(
    () => parseClaimUiBundle(bundle),
    "must contain query ref or query text",
  );
});

test("rejects unsupported fields under schema v1", () => {
  const bundle = validBundle();
  bundle.claims[0].confidence = 0.92;

  expectBundleError(
    () => parseClaimUiBundle(bundle),
    "unsupported field",
  );
});

test("rejects invalid logged timestamps before rendering", () => {
  const bundle = validBundle();
  bundle.claims[0].logged_at = "sometime yesterday";

  expectBundleError(
    () => parseClaimUiBundle(bundle),
    "logged_at",
  );
});
