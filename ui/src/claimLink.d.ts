export function readClaimFragment(hash: string): string | null;
export function findLinkedClaimId(
  hash: string,
  availableIds: readonly string[],
): string | null;
export function claimDeepLink(href: string, claimId: string): string;
