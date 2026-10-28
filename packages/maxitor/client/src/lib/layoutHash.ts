// src/lib/layoutHash.ts
/**
 * A short fingerprint of where a diagram put its nodes, equal only when every node is in
 * exactly the same place.
 *
 * Every viewer writes it on its diagram element as `data-layout-hash`; the tests, the check
 * run's cross-engine step and the room all read it from there (contracts/layout-determinism.md).
 */

/** Hex form of a digest. */
function toHex(digest: ArrayBuffer): string {
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

/**
 * SHA-256, hex, of the positions as little-endian `Float64` pairs ``[x0, y0, x1, y1, …]`` in the
 * order of ``nodeIds``; the bits are hashed, so two layouts differing in the last bit differ here.
 */
export async function layoutHash(
  positions: Record<string, [number, number]>,
  nodeIds: readonly string[],
): Promise<string> {
  const view = new DataView(new ArrayBuffer(nodeIds.length * 16));
  nodeIds.forEach((id, index) => {
    const [x, y] = positions[id];
    view.setFloat64(index * 16, x, true);
    view.setFloat64(index * 16 + 8, y, true);
  });
  return toHex(await crypto.subtle.digest("SHA-256", view.buffer));
}

/** SHA-256, hex, of the SVG markup Graphviz returned, which fixes every node's position. */
export async function svgLayoutHash(svg: string): Promise<string> {
  return toHex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(svg)));
}
