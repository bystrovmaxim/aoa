// src/lib/mapLevels.test.ts
import { describe, expect, it } from "vitest";
import { LEVEL_SCREEN_PX, LEVEL_THREE_BAND, LEVEL_TWO_BAND, levelAt, openingRatio, revealOf, widthAtRatio } from "./mapLevels";

describe("the map's levels", () => {
  it("reveals nothing before a band, everything after it, and eases between", () => {
    expect(revealOf(9000, LEVEL_TWO_BAND)).toBe(0);
    expect(revealOf(1000, LEVEL_TWO_BAND)).toBe(1);
    const middle = revealOf(6400, LEVEL_TWO_BAND);
    expect(middle).toBeGreaterThan(0.4);
    expect(middle).toBeLessThan(0.6);
  });

  it("takes the level from the width alone", () => {
    expect(levelAt(20000)).toBe(1);
    expect(levelAt(LEVEL_TWO_BAND[0] - 1)).toBe(2);
    expect(levelAt(LEVEL_THREE_BAND[0] - 1)).toBe(3);
  });
});

describe("the level at a zoom", () => {
  it("reads the same width of map on every screen", () => {
    expect(widthAtRatio(2)).toBe(2 * LEVEL_SCREEN_PX);
    expect(levelAt(widthAtRatio(0.5))).toBe(3);
    expect(levelAt(widthAtRatio(6))).toBe(1);
  });

  it("opens a map of one domain or none one level closer, and leaves a map of many fitted", () => {
    expect(levelAt(widthAtRatio(openingRatio(9, 1)))).toBe(2);
    expect(openingRatio(9, 0)).toBeLessThan(9);
    expect(openingRatio(9, 2)).toBe(9);
    expect(openingRatio(0.5, 1)).toBe(0.5);
  });
});
