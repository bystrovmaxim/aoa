// src/rooms/follow.test.ts
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Point } from "@/rooms/coordinates";
import type { DiagramSurface, SavedView } from "@/rooms/diagramSurface";
import { GLIDE_MAX_MS, createGlide, followCentre, followHead, followNavigation, followTarget, followZoom, useFollow, watchOwnPan } from "@/rooms/follow";
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

  it("centres on the centre of their screen", () => {
    expect(followCentre({ cx: 5, cy: 6, w: 4000, h: 3000 })).toEqual({ x: 5, y: 6 });
    expect(followCentre(undefined)).toBeNull();
  });

  it("goes one to one when they tell their screen's size: their zoom, and their top-left corner on yours (spec 038)", () => {
    // Theirs: 1200 × 800 px showing 2400 × 1600 units from (0, 0) — half a pixel a unit. Yours: 600 × 400 px at zoom 1,
    // showing 600 × 400 units: a pixel a unit, so their zoom is half yours, and your top-left corner goes to (0, 0).
    const target = followTarget({ w: 600, h: 400 }, { cx: 0, cy: 0, w: 600, h: 400 }, { cx: 1200, cy: 800, w: 2400, h: 1600, pw: 1200, ph: 800 }, 1);
    expect(target).toEqual({ centre: { x: 600, y: 400 }, zoom: 0.5 });
  });

  it("falls back to their centre, fitting their area, when they do not tell their screen's size", () => {
    expect(followTarget({ w: 600, h: 400 }, { cx: 0, cy: 0, w: 600, h: 400 }, { cx: 5, cy: 6, w: 1200, h: 800 }, 1)).toEqual({ centre: { x: 5, y: 6 }, zoom: 0.5 });
  });

  it("takes their zoom: the same on a screen of the same size, all of their area on another (spec 038)", () => {
    const yours = { cx: 0, cy: 0, w: 1000, h: 500 };
    expect(followZoom(yours, { cx: 0, cy: 0, w: 2000, h: 1000 }, 1)).toBe(0.5);
    expect(followZoom(yours, { cx: 0, cy: 0, w: 500, h: 500 }, 1)).toBeNull();
    expect(followZoom(yours, { cx: 0, cy: 0, w: 500, h: 100 }, 1)).toBe(2);
    expect(followZoom(yours, { cx: 0, cy: 0, w: 1004, h: 502 }, 1)).toBeNull();
  });
});

describe("following", () => {
  it("keeps this tab on their page and centre", () => {
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

  it("takes their zoom with their centre, and again whenever their zoom changes", () => {
    const view = surface();
    view.element.getBoundingClientRect = () => ({ left: 0, top: 0, right: 1000, bottom: 500, width: 1000, height: 500, x: 0, y: 0, toJSON: () => ({}) });
    let zoom = 1;
    view.view = () => ({ x: 0, y: 0, zoom });
    // What the screen shows in diagram units shrinks as the zoom grows, as on a real diagram.
    view.toDiagram = (client) => ({ x: client.x / zoom, y: client.y / zoom });
    view.restore.mockImplementation((next) => {
      zoom = next.zoom;
    });
    vi.useFakeTimers();
    renderHook(() => useFollow({ room: roomWith({ anna: "boris" }, ERD), send: vi.fn(), surface: view, page: ERD, navigate: vi.fn() }));
    act(() => putViewport("boris", { cx: 40, cy: -10, w: 2000, h: 1000 }));
    act(() => vi.advanceTimersByTime(GLIDE_MAX_MS + 50));
    expect(view.restore).toHaveBeenLastCalledWith({ x: 40, y: -10, zoom: 0.5 });
    // A zoom they make glides here: on the way it passes between the two, and it ends exactly on theirs.
    act(() => putViewport("boris", { cx: 40, cy: -10, w: 500, h: 250 }));
    act(() => vi.advanceTimersByTime(17));
    const between = view.restore.mock.calls.at(-1)![0].zoom;
    act(() => vi.advanceTimersByTime(GLIDE_MAX_MS + 50));
    vi.useRealTimers();
    expect(between).toBeGreaterThan(0.5);
    expect(between).toBeLessThan(2);
    expect(view.restore).toHaveBeenLastCalledWith({ x: 40, y: -10, zoom: 2 });
  });

  it("switches with one message: Follow <name> instead", () => {
    const send = vi.fn();
    const hook = renderHook(() => useFollow({ room: roomWith({ anna: "boris" }, ERD), send, surface: null, page: ERD, navigate: vi.fn() }));
    hook.result.current.follow("vera");
    // The tab's focus goes out too (spec 029); following itself is one message.
    const follows = send.mock.calls.filter(([message]) => message.type !== "focus");
    expect(follows).toEqual([[{ type: "follow", target: "vera" }]]);
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

  it("stop following on a wheel that moves the view: a trackpad swipe or a plain wheel (FR-053)", () => {
    const element = document.createElement("div");
    const onPan = vi.fn();
    const stop = watchOwnPan(element, onPan);
    element.dispatchEvent(new WheelEvent("wheel", { deltaX: 14, deltaY: -3 }));
    stop();
    expect(onPan).toHaveBeenCalledTimes(1);
  });

  it("do not stop it on a zoom: a pinch, Ctrl or ⌘ with the wheel, or a two-finger touch pinch", () => {
    const element = document.createElement("div");
    const onPan = vi.fn();
    const stop = watchOwnPan(element, onPan);
    element.dispatchEvent(new WheelEvent("wheel", { deltaY: -3, ctrlKey: true }));
    element.dispatchEvent(new WheelEvent("wheel", { deltaY: -120, metaKey: true }));
    element.dispatchEvent(pointer("pointerdown", 1, 100));
    element.dispatchEvent(pointer("pointerdown", 2, 200));
    window.dispatchEvent(pointer("pointermove", 1, 80));
    window.dispatchEvent(pointer("pointermove", 2, 230));
    stop();
    expect(onPan).not.toHaveBeenCalled();
  });
});

describe("the follower's glide (spec 029, FR-014, SC-003)", () => {
  const SCREEN = 2000;
  const FRAME = 1000 / 60;

  /** The leader pans 300 px every 200 ms — 0.15 of the follower's screen per screen they report. */
  function framesOfAPan(): { x: number; at: number }[] {
    const glide = createGlide();
    glide.jump({ x: 0, y: 0 }, 0);
    const frames: { x: number; at: number }[] = [];
    let next = 200;
    let x = 0;
    for (let now = 0; now <= 1600; now += FRAME) {
      if (now >= next && next <= 1000) {
        x += 300;
        glide.push({ x, y: 0 }, now);
        next += 200;
      }
      frames.push({ x: glide.at(now).point.x, at: now });
    }
    return frames;
  }

  it("moves on every frame and never jumps more than a tenth of the screen", () => {
    const frames = framesOfAPan();
    const steps = frames.slice(1).map((frame, i) => frame.x - frames[i]!.x);
    expect(Math.max(...steps)).toBeLessThanOrEqual(SCREEN / 10);
    expect(steps.every((step) => step >= 0)).toBe(true);
  });

  it("stands exactly where the leader stopped within half a second", () => {
    const frames = framesOfAPan();
    const settled = frames.filter((frame) => frame.at >= 1000 + 500);
    expect(settled.every((frame) => frame.x === 1500)).toBe(true);
  });

  it("never glides longer than its longest interval, however long the leader was still", () => {
    const glide = createGlide();
    glide.jump({ x: 0, y: 0 }, 0);
    glide.push({ x: 500, y: 0 }, 10_000);
    expect(glide.at(10_000 + GLIDE_MAX_MS)).toEqual({ point: { x: 500, y: 0 }, arrived: true });
  });

  it("drives the follower's screen frame by frame and ends on the leader's centre", () => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"] });
    try {
      const view = surface();
      renderHook(() => useFollow({ room: roomWith({ anna: "boris" }, ERD), send: vi.fn(), surface: view, page: ERD, navigate: vi.fn() }));
      act(() => putViewport("boris", { cx: 0, cy: 0, w: 2000, h: 1000 }));
      act(() => vi.advanceTimersByTime(200));
      act(() => putViewport("boris", { cx: 300, cy: 0, w: 2000, h: 1000 }));
      act(() => vi.advanceTimersByTime(100));
      const midway = view.centreOn.mock.calls.at(-1)![0];
      expect(midway.x).toBeGreaterThan(0);
      expect(midway.x).toBeLessThan(300);
      act(() => vi.advanceTimersByTime(300));
      expect(view.centreOn).toHaveBeenLastCalledWith({ x: 300, y: 0 });
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("following a follower (spec 038)", () => {
  it("takes the view from the end of the chain, while whom you follow stays whom you chose", () => {
    // Anna follows Boris, who follows Vera.
    expect(followHead(roomWith({ anna: "boris", boris: "vera", vera: null }, ERD))?.id).toBe("vera");
  });

  it("takes it from the one you follow once they follow nobody", () => {
    expect(followHead(roomWith({ anna: "boris", boris: null, vera: null }, ERD))?.id).toBe("boris");
    expect(followHead(roomWith({ anna: null, boris: null, vera: null }, ERD))).toBeNull();
  });

  it("never comes back to you, even through a circle the server would refuse", () => {
    expect(followHead(roomWith({ anna: "boris", boris: "anna", vera: null }, ERD))?.id).toBe("boris");
  });
});
