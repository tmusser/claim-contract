import type { ClaimGraphEdge, ClaimNode } from "./types";

export interface NodePosition {
  x: number;
  y: number;
}

export interface GraphLayout {
  positions: Record<string, NodePosition>;
  width: number;
  height: number;
}

const NODE_WIDTH = 254;
const NODE_HEIGHT = 108;
const X_GAP = 132;
const Y_GAP = 42;
const MARGIN_X = 70;
const MARGIN_Y = 64;

export const nodeWidth = NODE_WIDTH;
export const nodeHeight = NODE_HEIGHT;

export function layoutClaimGraph(
  claims: ClaimNode[],
  edges: ClaimGraphEdge[],
  roots: string[],
): GraphLayout {
  const claimIds = new Set(claims.map((claim) => claim.id));
  const outgoing = new Map<string, string[]>();
  for (const claim of claims) {
    outgoing.set(claim.id, []);
  }
  for (const edge of edges) {
    if (claimIds.has(edge.from) && claimIds.has(edge.to)) {
      outgoing.get(edge.from)?.push(edge.to);
    }
  }

  const rootSet = new Set(roots);
  const memo = new Map<string, number | null>();

  const rankFor = (id: string, visiting: Set<string>): number | null => {
    if (rootSet.has(id)) return 0;
    if (memo.has(id)) return memo.get(id) ?? null;
    if (visiting.has(id)) return null;

    const nextVisiting = new Set(visiting);
    nextVisiting.add(id);
    const targetRanks = (outgoing.get(id) ?? [])
      .map((target) => rankFor(target, nextVisiting))
      .filter((rank): rank is number => rank !== null);

    const rank =
      targetRanks.length > 0 ? Math.min(...targetRanks) + 1 : null;
    memo.set(id, rank);
    return rank;
  };

  const preliminary = new Map<string, number | null>();
  for (const claim of claims) {
    preliminary.set(claim.id, rankFor(claim.id, new Set()));
  }

  const connectedRanks = [...preliminary.values()].filter(
    (rank): rank is number => rank !== null,
  );
  const disconnectedRank =
    connectedRanks.length > 0 ? Math.max(...connectedRanks) + 1 : 1;

  const layers = new Map<number, ClaimNode[]>();
  for (const claim of claims) {
    const rank = preliminary.get(claim.id) ?? disconnectedRank;
    const layer = layers.get(rank) ?? [];
    layer.push(claim);
    layers.set(rank, layer);
  }

  for (const layer of layers.values()) {
    layer.sort((a, b) => a.id.localeCompare(b.id));
  }

  const maxRank = Math.max(0, ...layers.keys());
  const maxLayerSize = Math.max(1, ...[...layers.values()].map((layer) => layer.length));
  const width =
    MARGIN_X * 2 +
    (maxRank + 1) * NODE_WIDTH +
    maxRank * X_GAP;
  const height =
    MARGIN_Y * 2 +
    maxLayerSize * NODE_HEIGHT +
    Math.max(0, maxLayerSize - 1) * Y_GAP;

  const positions: Record<string, NodePosition> = {};
  for (const [rank, layer] of layers) {
    const layerHeight =
      layer.length * NODE_HEIGHT + Math.max(0, layer.length - 1) * Y_GAP;
    const startY = (height - layerHeight) / 2;
    layer.forEach((claim, index) => {
      positions[claim.id] = {
        x: MARGIN_X + rank * (NODE_WIDTH + X_GAP),
        y: startY + index * (NODE_HEIGHT + Y_GAP),
      };
    });
  }

  return { positions, width, height };
}

export function edgePath(
  source: NodePosition,
  target: NodePosition,
): string {
  const sx = source.x;
  const sy = source.y + NODE_HEIGHT / 2;
  const tx = target.x + NODE_WIDTH;
  const ty = target.y + NODE_HEIGHT / 2;
  const bend = Math.max(tx + 34, (sx + tx) / 2);

  return `M ${sx} ${sy} C ${bend} ${sy}, ${bend} ${ty}, ${tx} ${ty}`;
}
