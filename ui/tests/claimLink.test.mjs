import assert from "node:assert/strict";
import test from "node:test";

import {
  claimDeepLink,
  findLinkedClaimId,
  readClaimFragment,
} from "../src/claimLink.js";

test("reads only a canonical v1 claim fragment", () => {
  assert.equal(readClaimFragment("#claim=CCL-002"), "CCL-002");
  for (const hash of [
    "",
    "#section",
    "#claim=CCL-2",
    "#claim=CCL-0002",
    "#claim=CCL-002&status=OPEN",
    "#claim=CCL-002%0A",
    "#claim=not-a-claim",
  ]) {
    assert.equal(readClaimFragment(hash), null, hash);
  }
});

test("accepts links only to claims present in the loaded bundle", () => {
  const ids = ["CCL-001", "CCL-003"];
  assert.equal(findLinkedClaimId("#claim=CCL-003", ids), "CCL-003");
  assert.equal(findLinkedClaimId("#claim=CCL-002", ids), null);
  assert.equal(findLinkedClaimId("#unrelated", ids), null);
});

test("creates an exact claim deep link without altering hosting path or query", () => {
  assert.equal(
    claimDeepLink(
      "https://example.test/subpath/?view=graph#old-anchor",
      "CCL-003",
    ),
    "https://example.test/subpath/?view=graph#claim=CCL-003",
  );
});

test("claim deep links reject noncanonical identifiers", () => {
  for (const id of ["CCL-7", "CCL-0001", "CCL-001&x=y", "bad"]) {
    assert.throws(
      () => claimDeepLink("https://example.test/", id),
      /CCL-###/,
    );
  }
});
