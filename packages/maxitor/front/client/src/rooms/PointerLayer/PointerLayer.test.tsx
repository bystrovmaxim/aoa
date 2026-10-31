// src/rooms/PointerLayer/PointerLayer.test.tsx
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { DiagramSurface } from "@/rooms/diagramSurface";
import { clearPointers, putClick, putPointer } from "@/rooms/pointerStore";
import type { Participant } from "@/rooms/protocol";
import { PointerLayer, pointerVisible, RIPPLE_MS, TOUCH_MS } from "@/rooms/PointerLayer";

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

describe("the pointers over the page (spec 038)", () => {
  afterEach(() => {
    cleanup();
    clearPointers();
  });

  // The diagram fills 100 … 500 × 100 … 400 of a 1024 × 768 window; its coordinates are the window's.
  const element = document.createElement("div");
  element.getBoundingClientRect = () => ({ left: 100, top: 100, right: 500, bottom: 400, width: 400, height: 300 }) as DOMRect;
  const surface: DiagramSurface = { element, toDiagram: (c) => c, toClient: (p) => p, subscribe: () => () => undefined, centreOn: () => undefined, view: () => null, restore: () => undefined };
  const boris: Participant = { id: "boris", name: "Boris", colour: "#dc2626", page: "p", visible: true, away: false };
  const placed = () => document.querySelector<HTMLElement>('[data-participant="boris"]');

  it("show the followed person's pointer where it is — over a panel outside the diagram too", () => {
    putPointer("boris", { x: 40, y: 30, kind: "mouse", at: Date.now() });
    render(<PointerLayer surface={surface} participants={[boris]} followed="boris" />);
    const style = getComputedStyle(placed()!);
    expect([style.left, style.top]).toEqual(["38px", "28px"]);
  });

  it("put a pointer over a panel on the same spot of the screen, from the diagram's corner, whatever the diagram shows", () => {
    putPointer("boris", { x: -60, y: 20, kind: "mouse", at: Date.now(), frame: "screen" });
    render(<PointerLayer surface={surface} participants={[boris]} followed="boris" />);
    const style = getComputedStyle(placed()!);
    expect([style.left, style.top]).toEqual(["38px", "118px"]);
  });

  it("show anyone else's pointer off the diagram as an arrow at its edge", () => {
    putPointer("boris", { x: 40, y: 30, kind: "mouse", at: Date.now() });
    render(<PointerLayer surface={surface} participants={[boris]} />);
    expect(placed()?.getAttribute("title")).toBe("Boris — show");
  });

  it("show a click as a ripple for a moment", () => {
    putClick("boris", { x: 200, y: 200, at: Date.now() });
    const { unmount } = render(<PointerLayer surface={surface} participants={[boris]} />);
    expect(document.querySelector('[data-click="boris"]')).not.toBeNull();
    unmount();
    putClick("boris", { x: 200, y: 200, at: Date.now() - RIPPLE_MS - 1 });
    render(<PointerLayer surface={surface} participants={[boris]} />);
    expect(document.querySelector('[data-click="boris"]')).toBeNull();
  });
});

