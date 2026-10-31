// src/lib/mapOutline.test.ts
import { describe, expect, it } from "vitest";
import { outlineOf } from "./mapOutline";

const extent = (loop: [number, number][]) => [Math.min(...loop.map((p) => p[0])), Math.max(...loop.map((p) => p[0]))];

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

  it("has nothing to draw around nothing", () => {
    expect(outlineOf([])).toEqual([]);
  });
});
