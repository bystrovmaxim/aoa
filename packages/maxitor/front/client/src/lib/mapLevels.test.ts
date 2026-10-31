// src/lib/mapLevels.test.ts
import { describe, expect, it } from "vitest";
import { LEVEL_THREE_BAND, LEVEL_TWO_BAND, levelAt, revealOf } from "./mapLevels";

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
