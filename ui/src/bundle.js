const CLAIM_ID = /^CCL-[0-9]{3}$/;
const SHA256 = /^[0-9a-f]{64}$/;
const UI_SCOPE_NOTICE =
  "The claim map UI visualizes declared graph, ledger, and provenance metadata only. It does not verify evidence, execute queries, adjudicate claims, or mutate source artifacts.";

const TOP_LEVEL_KEYS = new Set([
  "schema_version",
  "type",
  "scientific_validation",
  "automatic_adjudication",
  "read_only",
  "scope_notice",
  "generated_from",
  "graph",
  "claims",
]);

const CLAIM_KEYS = new Set([
  "id",
  "status",
  "classification",
  "is_root",
  "claim",
  "scope",
  "decision_impact",
  "logged_at",
  "generated_at",
  "record_ref",
  "provenance_note",
  "context_snapshot",
  "source_files",
  "data_sources",
  "judgment",
]);

const CLASSIFICATIONS = new Set([
  "ROOT",
  "CONNECTED",
  "PRUNE_CANDIDATE",
  "RETIRED",
]);

export class ClaimBundleError extends Error {
  constructor(path, message) {
    super(`Invalid claim map bundle at ${path}: ${message}`);
    this.name = "ClaimBundleError";
    this.path = path;
  }
}

export function parseClaimUiBundle(value) {
  const root = expectObject(value, "$");
  rejectUnknown(root, TOP_LEVEL_KEYS, "$");

  expectConst(root.schema_version, "1.0", "$.schema_version");
  expectConst(
    root.type,
    "claim_contract.claim_ui_bundle",
    "$.type",
  );
  expectConst(root.scientific_validation, false, "$.scientific_validation");
  expectConst(
    root.automatic_adjudication,
    false,
    "$.automatic_adjudication",
  );
  expectConst(root.read_only, true, "$.read_only");
  expectConst(root.scope_notice, UI_SCOPE_NOTICE, "$.scope_notice");

  validateGeneratedFrom(root.generated_from, "$.generated_from");
  const graph = validateGraph(root.graph, "$.graph");
  const claims = expectArray(root.claims, "$.claims").map((claim, index) =>
    validateClaim(claim, `$.claims[${index}]`),
  );

  validateGraphReferences(graph, claims);

  return root;
}

function validateGeneratedFrom(value, path) {
  const object = expectObject(value, path);
  rejectUnknown(
    object,
    new Set(["ledger", "graph", "provenance"]),
    path,
  );
  expectNonEmptyString(object.ledger, `${path}.ledger`);
  expectNonEmptyString(object.graph, `${path}.graph`);
  expectNullableNonEmptyString(object.provenance, `${path}.provenance`);
}

function validateGraph(value, path) {
  const object = expectObject(value, path);
  rejectUnknown(object, new Set(["scope_notice", "roots", "edges"]), path);
  expectNonEmptyString(object.scope_notice, `${path}.scope_notice`);

  const roots = expectArray(object.roots, `${path}.roots`).map(
    (root, index) => {
      const id = expectClaimId(root, `${path}.roots[${index}]`);
      return id;
    },
  );
  expectUnique(roots, `${path}.roots`);

  const edges = expectArray(object.edges, `${path}.edges`).map(
    (edge, index) => validateEdge(edge, `${path}.edges[${index}]`),
  );

  const edgeKeys = edges.map((edge) => `${edge.from}->${edge.to}`);
  expectUnique(edgeKeys, `${path}.edges`);

  return { roots, edges };
}

function validateEdge(value, path) {
  const object = expectObject(value, path);
  rejectUnknown(object, new Set(["from", "to", "rationale"]), path);

  const from = expectClaimId(object.from, `${path}.from`);
  const to = expectClaimId(object.to, `${path}.to`);
  expectNonEmptyString(object.rationale, `${path}.rationale`);

  if (from === to) {
    fail(path, "self-edges are not valid claim-graph relationships");
  }

  return {
    from,
    to,
    rationale: object.rationale,
  };
}

function validateClaim(value, path) {
  const object = expectObject(value, path);
  rejectUnknown(object, CLAIM_KEYS, path);

  const id = expectClaimId(object.id, `${path}.id`);
  expectNonEmptyString(object.status, `${path}.status`);

  if (
    typeof object.classification !== "string" ||
    !CLASSIFICATIONS.has(object.classification)
  ) {
    fail(
      `${path}.classification`,
      "must be ROOT, CONNECTED, PRUNE_CANDIDATE, or RETIRED",
    );
  }

  expectBoolean(object.is_root, `${path}.is_root`);
  expectNonEmptyString(object.claim, `${path}.claim`);
  expectNonEmptyString(object.scope, `${path}.scope`);
  expectNonEmptyString(object.decision_impact, `${path}.decision_impact`);
  expectDateTime(object.logged_at, `${path}.logged_at`);
  expectNullableDateTime(object.generated_at, `${path}.generated_at`);
  expectNonEmptyString(object.record_ref, `${path}.record_ref`);
  expectNullableNonEmptyString(
    object.provenance_note,
    `${path}.provenance_note`,
  );
  expectObject(object.context_snapshot, `${path}.context_snapshot`);
  expectObject(object.judgment, `${path}.judgment`);

  const sourceFiles = expectArray(
    object.source_files,
    `${path}.source_files`,
  ).map((source, index) =>
    validateSourceFile(source, `${path}.source_files[${index}]`),
  );

  const dataSources = expectArray(
    object.data_sources,
    `${path}.data_sources`,
  ).map((source, index) =>
    validateDataSource(source, `${path}.data_sources[${index}]`),
  );

  return {
    ...object,
    id,
    source_files: sourceFiles,
    data_sources: dataSources,
  };
}

function validateSourceFile(value, path) {
  const object = expectObject(value, path);
  rejectUnknown(object, new Set(["ref", "roles", "note"]), path);
  const ref = expectNonEmptyString(object.ref, `${path}.ref`);

  const roles = expectArray(object.roles, `${path}.roles`).map(
    (role, index) =>
      expectNonEmptyString(role, `${path}.roles[${index}]`),
  );
  if (roles.length === 0) {
    fail(`${path}.roles`, "must contain at least one role");
  }
  expectUnique(roles, `${path}.roles`);

  if (Object.hasOwn(object, "note")) {
    expectNullableString(object.note, `${path}.note`);
  }

  return object;
}

function validateDataSource(value, path) {
  const object = expectObject(value, path);
  rejectUnknown(
    object,
    new Set([
      "system",
      "catalog",
      "database",
      "schema",
      "table",
      "query",
      "note",
    ]),
    path,
  );

  expectNonEmptyString(object.system, `${path}.system`);
  expectOptionalNonEmptyString(object.catalog, `${path}.catalog`);
  expectOptionalNonEmptyString(object.database, `${path}.database`);
  expectOptionalNonEmptyString(object.schema, `${path}.schema`);
  expectNonEmptyString(object.table, `${path}.table`);
  expectOptionalNonEmptyString(object.note, `${path}.note`);
  validateQuery(object.query, `${path}.query`);

  return object;
}

function validateQuery(value, path) {
  const object = expectObject(value, path);
  rejectUnknown(object, new Set(["ref", "text", "sha256"]), path);

  const hasRef = Object.hasOwn(object, "ref");
  const hasText = Object.hasOwn(object, "text");
  if (!hasRef && !hasText) {
    fail(path, "must contain query ref or query text");
  }

  expectOptionalNonEmptyString(object.ref, `${path}.ref`);
  expectOptionalNonEmptyString(object.text, `${path}.text`);

  if (Object.hasOwn(object, "sha256")) {
    const digest = expectNonEmptyString(object.sha256, `${path}.sha256`);
    if (!SHA256.test(digest)) {
      fail(`${path}.sha256`, "must be a lowercase 64-character SHA-256");
    }
  }
}

function validateGraphReferences(graph, claims) {
  const ids = claims.map((claim) => claim.id);
  expectUnique(ids, "$.claims");

  const known = new Set(ids);
  const rootSet = new Set(graph.roots);

  for (const root of graph.roots) {
    if (!known.has(root)) {
      fail("$.graph.roots", `references unknown claim ${root}`);
    }
  }

  for (const edge of graph.edges) {
    if (!known.has(edge.from)) {
      fail("$.graph.edges", `edge references unknown source claim ${edge.from}`);
    }
    if (!known.has(edge.to)) {
      fail("$.graph.edges", `edge references unknown target claim ${edge.to}`);
    }
  }

  for (const claim of claims) {
    const declaredRoot = rootSet.has(claim.id);
    if (claim.is_root !== declaredRoot) {
      fail(
        `$.claims[${claim.id}].is_root`,
        `must match graph.roots membership for ${claim.id}`,
      );
    }
    if (claim.classification === "ROOT" && !declaredRoot) {
      fail(
        `$.claims[${claim.id}].classification`,
        "ROOT classification requires graph.roots membership",
      );
    }
    if (declaredRoot && claim.classification !== "ROOT") {
      fail(
        `$.claims[${claim.id}].classification`,
        "graph root must carry ROOT classification",
      );
    }
  }
}

function expectObject(value, path) {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    fail(path, "must be an object");
  }
  return value;
}

function expectArray(value, path) {
  if (!Array.isArray(value)) {
    fail(path, "must be an array");
  }
  return value;
}

function expectBoolean(value, path) {
  if (typeof value !== "boolean") {
    fail(path, "must be a boolean");
  }
  return value;
}

function expectClaimId(value, path) {
  const id = expectNonEmptyString(value, path);
  if (!CLAIM_ID.test(id)) {
    fail(path, "must match CCL-###");
  }
  return id;
}

function expectNonEmptyString(value, path) {
  if (typeof value !== "string" || value.trim().length === 0) {
    fail(path, "must be a non-empty string");
  }
  return value;
}

function expectNullableString(value, path) {
  if (value !== null && typeof value !== "string") {
    fail(path, "must be a string or null");
  }
  return value;
}

function expectNullableNonEmptyString(value, path) {
  if (value === null) return value;
  return expectNonEmptyString(value, path);
}

function expectOptionalNonEmptyString(value, path) {
  if (value === undefined) return value;
  return expectNonEmptyString(value, path);
}

function expectDateTime(value, path) {
  const text = expectNonEmptyString(value, path);
  if (Number.isNaN(Date.parse(text))) {
    fail(path, "must be a valid date-time string");
  }
  return text;
}

function expectNullableDateTime(value, path) {
  if (value === null) return value;
  return expectDateTime(value, path);
}

function expectConst(value, expected, path) {
  if (value !== expected) {
    fail(path, `must equal ${JSON.stringify(expected)}`);
  }
}

function expectUnique(values, path) {
  const seen = new Set();
  for (const value of values) {
    if (seen.has(value)) {
      fail(path, `contains duplicate value ${JSON.stringify(value)}`);
    }
    seen.add(value);
  }
}

function rejectUnknown(object, allowed, path) {
  const unknown = Object.keys(object).filter((key) => !allowed.has(key));
  if (unknown.length > 0) {
    fail(path, `contains unsupported field(s): ${unknown.sort().join(", ")}`);
  }
}

function fail(path, message) {
  throw new ClaimBundleError(path, message);
}
