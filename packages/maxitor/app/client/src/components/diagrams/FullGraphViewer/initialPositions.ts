// src/components/diagrams/FullGraphViewer/initialPositions.ts
/**
 * Where every node starts before the force simulation runs: the golden-angle spiral `d3-force`
 * would draw, computed so that every browser gets the same bits.
 *
 * `d3-force-3d` places a node that has no `x`/`y` with `Math.cos` and `Math.sin`. The ECMAScript
 * specification lets each engine approximate those two functions in its own way, so Chrome,
 * Safari and Firefox may disagree in the last bit, and 220 steps of a physics simulation grow
 * that bit into visibly different pictures. Here the angle advances by turning the previous unit
 * vector through a fixed angle — a multiplication by two constants — so only `+ − × ÷` and
 * `Math.sqrt` are used, which the specification requires to be exact and equal everywhere.
 */

/** Distance unit of the spiral; `d3-force` uses the same value for its own starting spiral. */
export const INITIAL_RADIUS = 10;

/**
 * Cosine and sine of the golden angle, π·(3 − √5) ≈ 2.399963229728653 radians, written as
 * numbers so no engine computes them.
 */
const GOLDEN_COS = -0.7373688780783197;
const GOLDEN_SIN = 0.6754902942615238;

/**
 * Starting positions for ``nodeIds``, in the given order: node *i* at radius
 * ``radius · sqrt(0.5 + i)``, each one turned a golden angle further than the one before.
 */
export function initialPositions(
  nodeIds: readonly string[],
  radius: number = INITIAL_RADIUS,
): Record<string, [number, number]> {
  const positions: Record<string, [number, number]> = {};
  let unitX = 1;
  let unitY = 0;
  nodeIds.forEach((id, index) => {
    const distance = radius * Math.sqrt(0.5 + index);
    positions[id] = [distance * unitX, distance * unitY];
    const nextX = unitX * GOLDEN_COS - unitY * GOLDEN_SIN;
    const nextY = unitX * GOLDEN_SIN + unitY * GOLDEN_COS;
    unitX = nextX;
    unitY = nextY;
  });
  return positions;
}
