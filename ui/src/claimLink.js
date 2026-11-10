// Keep static-browser claim links scoped to the v1 claim ID grammar.
const CLAIM_ID = /^CCL-[0-9]{3}$/;
const CLAIM_HASH = /^#claim=(CCL-[0-9]{3})$/;

export function readClaimFragment(hash) {
  return CLAIM_HASH.exec(hash)?.[1] ?? null;
}

export function findLinkedClaimId(hash, availableIds) {
  const claimId = readClaimFragment(hash);
  return claimId !== null && availableIds.includes(claimId) ? claimId : null;
}

export function claimDeepLink(href, claimId) {
  if (!CLAIM_ID.test(claimId)) {
    throw new TypeError("Claim link requires a CCL-### identifier");
  }
  const url = new URL(href);
  url.hash = `claim=${claimId}`;
  return url.toString();
}
