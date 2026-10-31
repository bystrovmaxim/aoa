// src/lib/mapOutline.test.ts
import { describe, expect, it } from "vitest";
import { outlineOf } from "./mapOutline";

const extent = (loop: [number, number][]) => [Math.min(...loop.map((p) => p[0])), Math.max(...loop.map((p) => p[0]))];

/** A step along a loop never spans more than a few squares of the field's grid: a longer one is a loop closed by a straight line. */
const STEP_LIMIT = 200;

function longestStep(loops: [number, number][][]): number {
  return Math.max(...loops.flatMap((loop) => loop.map((point, index) => {
    const next = loop[(index + 1) % loop.length];
    return Math.hypot(point[0] - next[0], point[1] - next[1]);
  })));
}

/** What a filter left of a real domain, whose contour once ran through a corner of the grid: ``[column, row, count]``. */
const MESSAGING_LEFT = { x: -108.0, y: -4886.9, cell: 194.4, cells: [[-7,-4,1],[-6,-4,1],[-6,-3,2],[-6,-2,1],[-6,-2,1],[-5,-4,2],[-5,-4,1],[-5,-3,1],[-5,-3,1],[-5,-2,1],[-4,-4,1],[-4,-3,1],[-4,-3,1],[-4,-3,1],[-4,-2,2],[-4,-2,1],[-3,-2,1],[-2,-2,2],[-2,-1,3],[-1,-1,1],[0,1,2],[0,1,1],[0,1,1],[0,2,1],[0,2,1],[0,3,1],[0,3,1],[0,4,1],[1,1,1],[1,2,1],[1,2,1],[1,2,1],[1,3,1],[1,3,1],[1,4,1],[1,4,1],[2,4,2]] as [number, number, number][] };

describe("an area's outline", () => {
  it("encloses what it is drawn around", () => {
    const [loop] = outlineOf([[0, 0], [300, 0]]);
    const [left, right] = extent(loop);
    expect(left).toBeLessThan(0);
    expect(right).toBeGreaterThan(300);
  });

  it("closes around what is left", () => {
    const all = outlineOf([[0, 0], [100, 0], [2000, 0]]);
    const left = outlineOf([[0, 0], [100, 0]]);
    expect(all).toHaveLength(2);
    expect(left).toHaveLength(1);
  });

  it("closes every loop when two crossings fall on one corner of the grid", () => {
    const { x, y, cell, cells } = MESSAGING_LEFT;
    const points = cells.map(([column, row, count]): [number, number, number] => [x + (column + 0.5) * cell, y + (row + 0.5) * cell, Math.min(3, 0.8 + count / 4)]);
    expect(longestStep(outlineOf(points, cell))).toBeLessThan(STEP_LIMIT);
  });

  it("closes every loop, whatever it is drawn around", () => {
    let seed = 7;
    const random = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (let round = 0; round < 150; round += 1) {
      const points = Array.from({ length: 3 + Math.floor(random() * 30) }, (): [number, number, number] => [random() * 3000, random() * 3000, 0.8 + random() * 2.2]);
      expect(longestStep(outlineOf(points, 120 + random() * 100))).toBeLessThan(STEP_LIMIT);
    }
  });

  it("has nothing to draw around nothing", () => {
    expect(outlineOf([])).toEqual([]);
  });
});
