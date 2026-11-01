// src/model/historyMode.test.ts
import { describe, expect, it } from "vitest";
import { hasPicker, modeOf, pickerSubtitle } from "./historyMode";

const v = (n: number) => Array.from({ length: n }, (_, i) => i);
const LIVE = "https://orders.example";

describe("the mode of what is open (FR-009a)", () => {
  it.each([
    ["M1", null],
    ["M2", { versions: v(12), live: null }],
    ["M3", { versions: v(1), live: null }],
    ["M4", { versions: v(12), live: LIVE }],
    ["M5", { versions: v(1), live: LIVE }],
    ["M6", { versions: v(0), live: LIVE }],
    ["M7", { versions: v(0), live: null }],
  ] as const)("%s", (mode, history) => {
    expect(modeOf(history)).toBe(mode);
  });

  it("has a picker in M2–M6 only", () => {
    expect(["M1", "M2", "M3", "M4", "M5", "M6", "M7"].map((mode) => hasPicker(mode as never))).toEqual([false, true, true, true, true, true, false]);
  });

  it("words the subtitle by count and Live", () => {
    expect([pickerSubtitle(12, false), pickerSubtitle(1, false), pickerSubtitle(12, true), pickerSubtitle(1, true), pickerSubtitle(0, true)]).toEqual([
      "12 versions",
      "1 version",
      "12 versions and Live",
      "1 version and Live",
      "0 versions and Live",
    ]);
  });
});
