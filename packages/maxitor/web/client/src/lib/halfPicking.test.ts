// src/lib/halfPicking.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { dimUnpaired, halfTracking, hoverAcross, inView, joinMirror, joinSteps, mirrorBoth, noteOf, reportHalfHover, setHalfTracking, stepBoth } from "@/lib/halfPicking";

afterEach(() => {
  reportHalfHover("a", null);
  reportHalfHover("b", null);
});

describe("one element across the halves", () => {
  it("passes a hover to the other half, not to its own", () => {
    reportHalfHover("a", { kind: "table", id: "x" });
    expect(hoverAcross("b")).toEqual({ kind: "table", id: "x" });
    expect(hoverAcross("a")).toBeNull();
  });

  it("says a box is in view only when it stands whole inside", () => {
    const stage = { left: 0, right: 100, top: 0, bottom: 100 };
    expect(inView({ left: 10, right: 20, top: 10, bottom: 20 }, stage)).toBe(true);
    expect(inView({ left: 90, right: 120, top: 10, bottom: 20 }, stage)).toBe(false);
    expect(inView({ left: 10, right: 20, top: -5, bottom: 20 }, stage)).toBe(false);
  });

  it("says why it cannot show an element, naming its version", () => {
    expect(noteOf("absent", "0.9.0")).toBe("Not in 0.9.0");
    expect(noteOf("hidden", "0.9.0")).toBe("Hidden by the filters");
    expect(noteOf("moved", "0.9.0")).toBe("Brought to the centre");
    expect(noteOf("in_view", "0.9.0")).toBeNull();
  });

  it("puts a drawing out while the hover or the selection has no pair, and back when neither does", () => {
    const root = document.createElement("div");
    dimUnpaired(root, "hover", true);
    expect(root.style.opacity).not.toBe("");
    dimUnpaired(root, "selection", true);
    dimUnpaired(root, "hover", false);
    expect(root.style.opacity).not.toBe("");
    dimUnpaired(root, "selection", false);
    expect(root.style.opacity).toBe("");
  });

  it("tracks by default, and a person can turn it off", () => {
    expect(halfTracking()).toBe(true);
    setHalfTracking(false);
    expect(halfTracking()).toBe(false);
    setHalfTracking(true);
  });

  it("shows a followed step in both halves, and a half that left hears nothing", () => {
    const [a, b] = [vi.fn(), vi.fn()];
    const leaveA = joinMirror("a", a);
    const leaveB = joinMirror("b", b);
    mirrorBoth(5, true);
    expect(a).toHaveBeenCalledWith(5, true);
    expect(b).toHaveBeenCalledWith(5, true);
    leaveA();
    mirrorBoth(null, false);
    expect(a).toHaveBeenCalledTimes(1);
    leaveB();
  });

  it("takes one step in both halves, and a half that left takes none", () => {
    const [a, b] = [vi.fn(), vi.fn()];
    const leaveA = joinSteps("a", a);
    const leaveB = joinSteps("b", b);
    stepBoth(3);
    expect(a).toHaveBeenCalledWith(3);
    expect(b).toHaveBeenCalledWith(3);
    leaveA();
    stepBoth(4);
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(2);
    leaveB();
  });
});
