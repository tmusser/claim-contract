import type { ClaimUiBundle } from "./types";

export class ClaimBundleError extends Error {
  readonly path: string;
}

export function parseClaimUiBundle(value: unknown): ClaimUiBundle;
