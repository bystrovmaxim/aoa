// src/rooms/goTo.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Point } from "@/rooms/coordinates";
import type { DiagramSurface, SavedView } from "@/rooms/diagramSurface";
import { centreOnParticipant, goToPoint } from "@/rooms/goTo";
import { clearPointers, putPointer, putViewport } from "@/rooms/pointerStore";

afterEach(() => clearPointers());

function surface() {
  const centreOn = vi.fn<(point: Point) => void>();
  const restore = vi.fn<(view: SavedView) => void>();
  const view: DiagramSurface = {
    element: document.createElement("div"),
    toDiagram: (c) => c,
    toClient: (p) => p,
    subscribe: () => () => undefined,
    centreOn,
    view: () => ({ x: 0, y: 0, zoom: 1.5 }),
    restore,
  };
  return Object.assign(view, { centreOn, restore });
}

describe("where going to someone centres", () => {
  it("is their pointer when they have one", () => {
    expect(goToPoint({ x: 1, y: 2, kind: "mouse", at: 0 }, { cx: 9, cy: 9, w: 100, h: 50 })).toEqual({ x: 1, y: 2 });
  });

  it("is the centre of their screen when they have no pointer", () => {
    expect(goToPoint(undefined, { cx: 9, cy: 8, w: 100, h: 50 })).toEqual({ x: 9, y: 8 });
  });

  it("is nowhere when nothing is known of them", () => {
    expect(goToPoint(undefined, undefined)).toBeNull();
  });
});

describe("going to someone", () => {
  it("centres on them and never touches the zoom", () => {
    const view = surface();
    putViewport("boris", { cx: 40, cy: -10, w: 2000, h: 1000 });
    expect(centreOnParticipant(view, "boris")).toBe(true);
    expect(view.centreOn).toHaveBeenCalledWith({ x: 40, y: -10 });
    expect(view.restore).not.toHaveBeenCalled();
    putPointer("boris", { x: 3, y: 4, kind: "touch", at: Date.now() });
    centreOnParticipant(view, "boris");
    expect(view.centreOn).toHaveBeenLastCalledWith({ x: 3, y: 4 });
    expect(view.restore).not.toHaveBeenCalled();
  });

  it("does nothing for someone whose position is unknown", () => {
    const view = surface();
    expect(centreOnParticipant(view, "nobody")).toBe(false);
    expect(view.centreOn).not.toHaveBeenCalled();
  });
});
