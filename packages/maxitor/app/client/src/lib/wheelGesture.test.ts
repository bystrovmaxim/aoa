// src/lib/wheelGesture.test.ts
import { describe, expect, it } from "vitest";
import { isZoomWheel, wheelPan } from "@/lib/wheelGesture";

const wheel = (init: Partial<WheelEvent>) => ({ deltaX: 0, deltaY: 0, deltaMode: 0, shiftKey: false, ctrlKey: false, metaKey: false, ...init });

describe("the wheel over a diagram (spec 029, FR-053)", () => {
  it("zooms on a pinch (the browser sets ctrlKey) and on Ctrl or ⌘ with the wheel", () => {
    expect(isZoomWheel(wheel({ ctrlKey: true, deltaY: -3.2 }))).toBe(true);
    expect(isZoomWheel(wheel({ metaKey: true, deltaY: 100 }))).toBe(true);
  });

  it("moves on a two-finger swipe or a plain wheel, by the swipe's own pixels", () => {
    expect(isZoomWheel(wheel({ deltaX: 12, deltaY: -7 }))).toBe(false);
    expect(wheelPan(wheel({ deltaX: 12, deltaY: -7 }), 800)).toEqual({ dx: 12, dy: -7 });
  });

  it("turns a wheel counted in lines or pages into pixels", () => {
    expect(wheelPan(wheel({ deltaY: 3, deltaMode: 1 }), 800)).toEqual({ dx: 0, dy: 48 });
    expect(wheelPan(wheel({ deltaY: 1, deltaMode: 2 }), 800)).toEqual({ dx: 0, dy: 800 });
  });

  it("moves sideways on Shift with a vertical wheel, and leaves a sideways swipe as it is", () => {
    expect(wheelPan(wheel({ deltaY: 100, shiftKey: true }), 800)).toEqual({ dx: 100, dy: 0 });
    expect(wheelPan(wheel({ deltaX: 100, shiftKey: true }), 800)).toEqual({ dx: 100, dy: 0 });
  });
});
