// src/lib/freshGraph.test.ts
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FINGERPRINT_POLL_MS, enabledKeys, startFingerprintPoll, useModelRefresh } from "@/lib/freshGraph";
import type { Point } from "@/rooms/coordinates";
import type { DiagramSurface, SavedView } from "@/rooms/diagramSurface";

function setVisibility(state: "visible" | "hidden") {
  Object.defineProperty(document, "visibilityState", { value: state, configurable: true });
  document.dispatchEvent(new Event("visibilitychange"));
}

function surface(view: SavedView | null) {
  const restore = vi.fn<(v: SavedView) => void>();
  const centreOn = vi.fn<(p: Point) => void>();
  const s: DiagramSurface = { element: document.createElement("div"), toDiagram: (c) => c, toClient: (p) => p, subscribe: () => () => undefined, centreOn, view: () => view, restore };
  return Object.assign(s, { restore });
}

describe("the fingerprint poll", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setVisibility("visible");
  });
  afterEach(() => {
    vi.useRealTimers();
    setVisibility("visible");
  });

  it("does nothing while Maxitor holds the graph the tab drew", async () => {
    const onChanged = vi.fn();
    const stop = startFingerprintPoll({ read: async () => "f1", known: () => "f1", onChanged });
    await vi.advanceTimersByTimeAsync(FINGERPRINT_POLL_MS * 3);
    stop();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("reports a new fingerprint", async () => {
    const onChanged = vi.fn();
    const stop = startFingerprintPoll({ read: async () => "f2", known: () => "f1", onChanged });
    await vi.advanceTimersByTimeAsync(FINGERPRINT_POLL_MS);
    stop();
    expect(onChanged).toHaveBeenCalledTimes(1);
    expect(onChanged).toHaveBeenCalledWith("f2");
  });

  it("does not ask while the tab is hidden, and asks at once when it comes back", async () => {
    const read = vi.fn(async () => "f1");
    const stop = startFingerprintPoll({ read, known: () => "f1", onChanged: vi.fn() });
    setVisibility("hidden");
    await vi.advanceTimersByTimeAsync(FINGERPRINT_POLL_MS * 4);
    expect(read).not.toHaveBeenCalled();
    setVisibility("visible");
    expect(read).toHaveBeenCalledTimes(1);
    stop();
  });
});

describe("refreshing the page in place", () => {
  it("re-reads once and puts the zoom and centre back on the new diagram", () => {
    const rereadSidebar = vi.fn();
    const redraw = vi.fn();
    const before = surface({ x: 10, y: 20, zoom: 1.75 });
    const hook = renderHook(({ s }) => useModelRefresh({ surface: s, rereadSidebar, redraw }), { initialProps: { s: before as DiagramSurface | null } });
    act(() => hook.result.current.refresh());
    expect(rereadSidebar).toHaveBeenCalledTimes(1);
    expect(redraw).toHaveBeenCalledTimes(1);
    expect(hook.result.current.updated).toBe(true);
    hook.rerender({ s: null });
    const after = surface(null);
    hook.rerender({ s: after });
    expect(after.restore).toHaveBeenCalledWith({ x: 10, y: 20, zoom: 1.75 });
    expect(before.restore).not.toHaveBeenCalled();
    // The viewer fits again as its data arrives: the view goes back on that surface too.
    const refitted = surface(null);
    hook.rerender({ s: refitted });
    expect(refitted.restore).toHaveBeenCalledWith({ x: 10, y: 20, zoom: 1.75 });
  });
});

describe("a filter after the model changed", () => {
  it("drops a domain the model no longer has", () => {
    expect(enabledKeys(["offers", "players"], ["players", "events"])).toEqual(["players"]);
  });

  it("falls back to all when it names nothing the model has, and keeps an empty choice empty", () => {
    expect(enabledKeys(["offers", "players"], ["events"])).toEqual(["offers", "players"]);
    expect(enabledKeys(["offers", "players"], [])).toEqual([]);
    expect(enabledKeys(["offers", "players"], null)).toEqual(["offers", "players"]);
  });
});
