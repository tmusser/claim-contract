import { readFile } from "node:fs/promises";
import process from "node:process";

import { parseClaimUiBundle } from "../src/bundle.js";

const path = process.argv[2];

if (!path) {
  console.error("Usage: node scripts/validate-bundle.mjs <claim-map.json>");
  process.exit(2);
}

try {
  const text = await readFile(path, "utf8");
  const raw = JSON.parse(text);
  const bundle = parseClaimUiBundle(raw);
  console.log(
    `Validated claim map bundle: ${bundle.claims.length} claims, ${bundle.graph.edges.length} edges.`,
  );
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
