// src/rooms/follow.test.ts
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Point } from "@/rooms/coordinates";
import type { DiagramSurface, SavedView } from "@/rooms/diagramSurface";
import { followCentre, followNavigation, useFollow, watchOwnPan } from "@/rooms/follow";
import { clearPointers, putViewport } from "@/rooms/pointerStore";
import type { Participant } from "@/rooms/protocol";
import type { RoomState } from "@/rooms/roomStore";

const ERD = "view=domain-erd";
const GRAPH = "view=full-graph";

afterEach(() => clearPointers());

function person(id: string, page: string): Participant {
  return { id, name: id, colour: "#2563eb", page, visible: true, away: false };
}

function roomWith(follows: Record<string, string | null>, boris: string): RoomState {
  return {
    roomId: "r1",
    source: "s",
    youId: "anna",
    createdBy: "anna",
    participants: [person("anna", ERD), person("boris", boris), person("vera", ERD)],
    settings: {},
    follows,
    serverBuild: "",
    fallbackPage: null,
    notices: [],
    graphVersion: 0,
  };
}

function surface() {
  const element = document.createElement("div");
  document.body.appendChild(element);
  const centreOn = vi.fn<(point: Point) => void>();
  const restore = vi.fn<(view: SavedView) => void>();
  const view: DiagramSurface = { element, toDiagram: (c) => c, toClient: (p) => p, subscribe: () => () => undefined, centreOn, view: () => null, restore };
  return Object.assign(view, { centreOn, restore });
}

function pointer(type: string, id: number, x: number, y = 0, button = 0): PointerEvent {
  const event = new Event(type, { bubbles: true }) as PointerEvent;
  Object.assign(event, { pointerId: id, clientX: x, clientY: y, button });
  return event;
}

describe("where following goes", () => {
  it("opens their page by replacing the history entry, and stays when already there", () => {
    expect(followNavigation(person("boris", GRAPH), ERD)).toEqual({ page: GRAPH, replace: true });
    expect(followNavigation(person("boris", ERD), ERD)).toBeNull();
  });

  it("centres on the centre of their screen, never on its size", () => {
    expect(followCentre({ cx: 5, cy: 6, w: 4000, h: 3000 })).toEqual({ x: 5, y: 6 });
    expect(followCentre(undefined)).toBeNull();
  });
});

describe("following", () => {
  it("keeps this tab on their page and centre at its own zoom", () => {
    const view = surface();
    const navigate = vi.fn();
    const hook = renderHook(
      ({ page }) => useFollow({ room: roomWith({ anna: "boris" }, GRAPH), send: vi.fn(), surface: view, page, navigate }),
      { initialProps: { page: ERD } },
    );
    expect(navigate).toHaveBeenCalledWith(GRAPH, { replace: true });
    hook.rerender({ page: GRAPH });
    act(() => putViewport("boris", { cx: 40, cy: -10, w: 2000, h: 1000 }));
    expect(view.centreOn).toHaveBeenLastCalledWith({ x: 40, y: -10 });
    expect(view.restore).not.toHaveBeenCalled();
    expect(hook.result.current.following?.id).toBe("boris");
  });

  it("switches with one message: Follow <name> instead", () => {
    const send = vi.fn();
    const hook = renderHook(() => useFollow({ room: roomWith({ anna: "boris" }, ERD), send, surface: null, page: ERD, navigate: vi.fn() }));
    hook.result.current.follow("vera");
    expect(send).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith({ type: "follow", target: "vera" });
  });

  it("stops on Esc", () => {
    const send = vi.fn();
    renderHook(() => useFollow({ room: roomWith({ anna: "boris" }, ERD), send, surface: null, page: ERD, navigate: vi.fn() }));
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(send).toHaveBeenCalledWith({ type: "stop_following" });
  });
});

describe("your own moves", () => {
  it("stop following on a drag (a pan)", () => {
    const element = document.createElement("div");
    const onPan = vi.fn();
    const stop = watchOwnPan(element, onPan);
    element.dispatchEvent(pointer("pointerdown", 1, 100));
    window.dispatchEvent(pointer("pointermove", 1, 110));
    stop();
    expect(onPan).toHaveBeenCalledTimes(1);
  });

  it("do not stop it on a zoom: the wheel or a two-finger pinch", () => {
    const element = document.createElement("div");
    const onPan = vi.fn();
    const stop = watchOwnPan(element, onPan);
    element.dispatchEvent(new WheelEvent("wheel", { deltaY: -120 }));
    element.dispatchEvent(pointer("pointerdown", 1, 100));
    element.dispatchEvent(pointer("pointerdown", 2, 200));
    window.dispatchEvent(pointer("pointermove", 1, 80));
    window.dispatchEvent(pointer("pointermove", 2, 230));
    stop();
    expect(onPan).not.toHaveBeenCalled();
  });
});
