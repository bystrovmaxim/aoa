// src/rooms/throttle.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DiagramSurface } from "@/rooms/diagramSurface";
import type { ClientMessage } from "@/rooms/protocol";
import { POINTER_RATE, throttle } from "@/rooms/throttle";
import { startPointerSender } from "@/rooms/usePointerSender";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("throttle", () => {
  it("sends at once, then the newest value at the end of the interval", () => {
    const sent: number[] = [];
    const t = throttle<number>(POINTER_RATE, (v) => sent.push(v), (a, b) => a === b);
    t.push(1);
    t.push(2);
    t.push(3);
    expect(sent).toEqual([1]);
    vi.advanceTimersByTime(50);
    expect(sent).toEqual([1, 3]);
  });

  it("never sends the same value twice", () => {
    const sent: number[] = [];
    const t = throttle<number>(POINTER_RATE, (v) => sent.push(v), (a, b) => a === b);
    t.push(1);
    vi.advanceTimersByTime(100);
    t.push(1);
    vi.advanceTimersByTime(100);
    expect(sent).toEqual([1]);
  });
});

describe("a tab moving its pointer and panning at once", () => {
  it("sends at most 40 messages in any one second: pointer 20 + screen 20 (spec 029, FR-016)", () => {
    const element = document.createElement("div");
    element.getBoundingClientRect = () => ({ left: 0, top: 0, right: 400, bottom: 300, width: 400, height: 300 }) as DOMRect;
    let pan = 0;
    const transforms = new Set<() => void>();
    const surface: DiagramSurface = {
      element,
      toDiagram: (c) => ({ x: c.x + pan, y: c.y }),
      toClient: (p) => ({ x: p.x - pan, y: p.y }),
      subscribe: (listener) => {
        transforms.add(listener);
        return () => transforms.delete(listener);
      },
      centreOn: () => undefined,
      view: () => null,
      restore: () => undefined,
    };
    const times: number[] = [];
    const stop = startPointerSender(surface, (_message: ClientMessage) => times.push(Date.now()));
    for (let ms = 0; ms < 3000; ms += 5) {
      pan += 1;
      for (const listener of transforms) listener();
      const move = new Event("pointermove") as PointerEvent;
      Object.assign(move, { clientX: 10 + ms, clientY: 20, pointerType: "mouse" });
      element.dispatchEvent(move);
      vi.advanceTimersByTime(5);
    }
    stop();
    const busiest = Math.max(...times.map((t) => times.filter((u) => u >= t && u < t + 1000).length));
    expect(times.length).toBeGreaterThan(60);
    expect(busiest).toBeLessThanOrEqual(40);
  });
});

describe("the pointer sender", () => {
  function sender() {
    const element = document.createElement("div");
    element.getBoundingClientRect = () => ({ left: 0, top: 0, right: 400, bottom: 300, width: 400, height: 300 }) as DOMRect;
    const surface: DiagramSurface = {
      element,
      toDiagram: (c) => ({ x: c.x * 4 + 1000, y: c.y * 4 - 500 }),
      toClient: (p) => ({ x: (p.x - 1000) / 4, y: (p.y + 500) / 4 }),
      subscribe: () => () => undefined,
      centreOn: () => undefined,
      view: () => null,
      restore: () => undefined,
    };
    const sent: ClientMessage[] = [];
    const stop = startPointerSender(surface, (message) => sent.push(message));
    // A panel over the page, outside the diagram: the filter panel, the version picker, the left panel.
    const panel = document.createElement("div");
    document.body.appendChild(panel);
    const press = (type: string, extra: Partial<PointerEvent>) => {
      const event = new Event(type, { bubbles: true }) as PointerEvent;
      Object.assign(event, { clientX: 100, clientY: 50, pointerType: "mouse", button: 0, ...extra });
      panel.dispatchEvent(event);
    };
    return { sent, press, stop: () => (stop(), panel.remove()) };
  }

  it("sends diagram coordinates, not screen pixels, and says whether it was a touch", () => {
    const { sent, press, stop } = sender();
    press("pointerdown", { pointerType: "touch" });
    stop();
    expect(sent.find((m) => m.type === "pointer")).toEqual({ type: "pointer", x: 1400, y: -300, kind: "touch" });
  });

  it("sends the pointer over a panel outside the diagram too (spec 038)", () => {
    const { sent, press, stop } = sender();
    press("pointermove", {});
    stop();
    expect(sent).toContainEqual({ type: "pointer", x: 1400, y: -300, kind: "mouse" });
  });

  it("sends a click where it happened — a left click of a mouse, not a tap nor another button", () => {
    const { sent, press, stop } = sender();
    press("pointerdown", {});
    press("pointerdown", { button: 2 });
    press("pointerdown", { pointerType: "touch" });
    stop();
    expect(sent.filter((m) => m.type === "click")).toEqual([{ type: "click", x: 1400, y: -300 }]);
  });
});
