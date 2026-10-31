// src/lib/mapOutline.ts
/**
 * An area's outline: a smooth field over weighted points, contoured by marching squares (spec 040, FR-029a). The
 * points are an area's nodes when they are loaded, and the cells of its sketch when they are not.
 */

/** One point of a field: where it is and how much it weighs. */
export type FieldPoint = readonly [x: number, y: number, weight?: number];

/** A closed outline in map units. */
export type OutlineLoop = [number, number][];

const GRID = 30;
const DEFAULT_REACH = 120;
const THRESHOLD = 0.34;
const SHORTEST_LOOP = 8;

type P = [number, number];

/** The two ends of the contour crossing one grid square, per pattern of its corners. */
function crossings(code: number, n: P, e: P, s: P, w: P): [P, P][] {
  const table: Record<number, [P, P][]> = { 1: [[w, n]], 2: [[n, e]], 3: [[w, e]], 4: [[e, s]], 5: [[w, n], [e, s]], 6: [[n, s]], 7: [[w, s]], 8: [[s, w]], 9: [[s, n]], 10: [[n, e], [s, w]], 11: [[s, e]], 12: [[e, w]], 13: [[e, n]], 14: [[n, w]] };
  return table[code] ?? [];
}

/** Join the crossings into closed loops. */
function loopsOf(pieces: [P, P][]): P[][] {
  const key = (point: P) => `${point[0].toFixed(3)},${point[1].toFixed(3)}`;
  const next = new Map(pieces.map((piece) => [key(piece[0]), piece]));
  const seen = new Set<string>();
  const loops: P[][] = [];
  for (const [start] of pieces) {
    const loop: P[] = [];
    let at = key(start);
    while (next.has(at) && !seen.has(at)) {
      seen.add(at);
      const [from, to] = next.get(at)!;
      loop.push(from);
      at = key(to);
    }
    if (loop.length > SHORTEST_LOOP) loops.push(loop);
  }
  return loops;
}

/** The outline around ``points``, one loop or several; ``reach`` is how far each point's field spreads. */
export function outlineOf(points: readonly FieldPoint[], reach = DEFAULT_REACH): OutlineLoop[] {
  if (points.length === 0) return [];
  const xs = points.map((point) => point[0]);
  const ys = points.map((point) => point[1]);
  const margin = 4 * reach;
  const left = Math.min(...xs) - margin;
  const top = Math.min(...ys) - margin;
  const width = Math.ceil((Math.max(...xs) + margin - left) / GRID);
  const height = Math.ceil((Math.max(...ys) + margin - top) / GRID);
  const field = new Float32Array((width + 1) * (height + 1));
  const spread = Math.ceil((reach * 3.2) / GRID);
  for (const [x, y, weight = 1] of points) {
    const column = Math.round((x - left) / GRID);
    const row = Math.round((y - top) / GRID);
    for (let j = Math.max(0, row - spread); j <= Math.min(height, row + spread); j += 1) {
      for (let i = Math.max(0, column - spread); i <= Math.min(width, column + spread); i += 1) {
        const dx = left + i * GRID - x;
        const dy = top + j * GRID - y;
        field[j * (width + 1) + i] += weight * Math.exp(-(dx * dx + dy * dy) / (reach * reach));
      }
    }
  }
  const at = (i: number, j: number) => field[j * (width + 1) + i];
  const along = (from: number, to: number) => (THRESHOLD - from) / (to - from);
  const pieces: [P, P][] = [];
  for (let j = 0; j < height; j += 1) {
    for (let i = 0; i < width; i += 1) {
      const [a, b, c, d] = [at(i, j), at(i + 1, j), at(i + 1, j + 1), at(i, j + 1)];
      const code = (a > THRESHOLD ? 1 : 0) | (b > THRESHOLD ? 2 : 0) | (c > THRESHOLD ? 4 : 0) | (d > THRESHOLD ? 8 : 0);
      if (code === 0 || code === 15) continue;
      pieces.push(...crossings(code, [i + along(a, b), j], [i + 1, j + along(b, c)], [i + along(d, c), j + 1], [i, j + along(a, d)]));
    }
  }
  return loopsOf(pieces).map((loop) => loop.filter((_, index) => index % 2 === 0).map(([i, j]): [number, number] => [left + i * GRID, top + j * GRID]));
}
