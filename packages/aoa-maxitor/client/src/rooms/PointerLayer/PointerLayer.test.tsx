// src/rooms/PointerLayer/PointerLayer.test.tsx
import { describe, expect, it } from "vitest";
import { pointerVisible, TOUCH_MS } from "@/rooms/PointerLayer";

describe("which pointers show (spec 029, FR-020 … FR-022)", () => {
  it("shows a mouse pointer however long it has stood still", () => {
    const pointer = { x: 1, y: 2, kind: "mouse" as const, at: 0 };
    expect(pointerVisible(pointer, 10 * 60 * 1000)).toBe(true);
  });

  it("shows a tap only for a moment", () => {
    const tap = { x: 1, y: 2, kind: "touch" as const, at: 0 };
    expect(pointerVisible(tap, TOUCH_MS - 1)).toBe(true);
    expect(pointerVisible(tap, TOUCH_MS)).toBe(false);
  });
});
