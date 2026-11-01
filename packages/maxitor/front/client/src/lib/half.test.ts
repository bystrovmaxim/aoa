// src/lib/half.test.ts
import { describe, expect, it } from "vitest";
import { drawnOn, settingOfHalf, svgOfHalf, writesForPair, type Half } from "@/lib/half";

const half = (side: "a" | "b"): Half => ({ side, read: { source: side, key: "" }, name: side });

describe("a half", () => {
  it("keeps its layout mode under its own name and shares every other setting", () => {
    expect(settingOfHalf("layout", half("a"))).toBe("layout_a");
    expect(settingOfHalf("rankdir", half("b"))).toBe("rankdir_b");
    expect(settingOfHalf("domains", half("a"))).toBe("domains");
    expect(settingOfHalf("layout", null)).toBe("layout");
  });

  it("keeps its clips apart from the other half's, so each drawing is cut by its own", () => {
    const svg = '<clipPath id="erd-fill-clip-node1"></clipPath><polygon clip-path="url(#erd-fill-clip-node1)"/>';
    expect(svgOfHalf(svg, half("b"))).toBe('<clipPath id="erd-fill-clip-b-node1"></clipPath><polygon clip-path="url(#erd-fill-clip-b-node1)"/>');
    expect(svgOfHalf(svg, half("a"))).not.toBe(svgOfHalf(svg, half("b")));
    expect(svgOfHalf(svg, null)).toBe(svg);
  });

  it("draws what its version has", () => {
    expect(drawnOn("a", "added")).toBe(false);
    expect(drawnOn("a", "removed")).toBe(true);
    expect(drawnOn("b", "removed")).toBe(false);
    expect(drawnOn("b", "added")).toBe(true);
    expect(drawnOn("a", "changed") && drawnOn("b", "unchanged")).toBe(true);
  });

  it("leaves what a pair has once to B, and to a viewer with no half", () => {
    expect(writesForPair(half("a"))).toBe(false);
    expect(writesForPair(half("b"))).toBe(true);
    expect(writesForPair(null)).toBe(true);
  });
});
