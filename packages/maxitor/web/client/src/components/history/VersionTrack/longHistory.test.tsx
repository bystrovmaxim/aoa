// src/components/history/VersionTrack/longHistory.test.tsx
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { MIN_STEP, VersionTrack } from "./VersionTrack";

/**
 * jsdom lays nothing out and scrolls nothing, so the browser's scrolling is stood in for: ``scrollLeft`` keeps
 * what it is given and says so with a ``scroll`` event, ``scrollTo`` and ``scrollBy`` set it, and an animation
 * frame runs at once.
 */
beforeEach(() => {
  const left = new WeakMap<HTMLElement, number>();
  Object.defineProperty(HTMLElement.prototype, "scrollLeft", {
    configurable: true,
    get(this: HTMLElement) {
      return left.get(this) ?? 0;
    },
    set(this: HTMLElement, value: number) {
      left.set(this, Math.max(0, value));
      this.dispatchEvent(new Event("scroll"));
    },
  });
  HTMLElement.prototype.scrollTo = function (this: HTMLElement, options?: ScrollToOptions | number) {
    if (typeof options === "object" && options.left !== undefined) this.scrollLeft = options.left;
  } as HTMLElement["scrollTo"];
  HTMLElement.prototype.scrollBy = function (this: HTMLElement, options?: ScrollToOptions | number) {
    if (typeof options === "object" && options.left !== undefined) this.scrollLeft += options.left;
  } as HTMLElement["scrollBy"];
  vi.stubGlobal("requestAnimationFrame", (run: FrameRequestCallback) => {
    run(0);
    return 0;
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const WIDTH = 520;
const LIVE = "https://live.example";

function versions(count: number, releaseEvery = 8): HistoryVersion[] {
  return Array.from({ length: count }, (_, i) => ({
    sha: `${i}`.padStart(6, "0").padEnd(40, "e"),
    date: "2026-10-01T00:00:00Z",
    tags: i % releaseEvery === 0 ? [{ name: `v0.${i}.0`, release: null }] : [],
    nodes: 1,
    edges: 1,
    source: `s${i}`,
    pr: { number: i, title: "", body: "", url: "" },
  }));
}
const id = (i: number) => `${i}`.padStart(6, "0").padEnd(12, "e");

function xs(): number[] {
  return screen.getAllByTestId(/^point-/).map((point) => Number(point.getAttribute("data-x")));
}
const offset = () => Number(screen.getByTestId("track").getAttribute("data-offset"));
const view = () => screen.getByTestId("track-view");

describe.each([
  ["M2", 64, null],
  ["M4", 64, LIVE],
  ["M2", 500, null],
  ["M4", 500, LIVE],
] as const)("a long history, %s with %i versions", (_mode, count, live) => {
  it("keeps points at least 24 px apart and scrolls as the browser scrolls, with nothing faded", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(count - 1)} onChange={() => undefined} width={WIDTH} />);
    const at = xs();
    for (let i = 1; i < count; i += 1) expect(at[i] - at[i - 1]).toBeGreaterThanOrEqual(MIN_STEP);
    expect(getComputedStyle(view()).overflowX).toBe("auto");
    expect(document.querySelector("linearGradient")).toBeNull();
  });

  it("opens with the chosen version in view", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(0)} onChange={() => undefined} width={WIDTH} />);
    expect(offset()).toBe(0);
    cleanup();
    render(<VersionTrack versions={versions(count)} live={live} value={id(count - 1)} onChange={() => undefined} width={WIDTH} />);
    const newest = Number(screen.getByTestId(`point-${id(count - 1)}`).getAttribute("data-x"));
    expect(newest).toBeGreaterThanOrEqual(offset());
    expect(newest).toBeLessThanOrEqual(offset() + WIDTH);
  });

  it("counts every point out of view on the right, Live included", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(0)} onChange={() => undefined} width={WIDTH} />);
    const hidden = xs().filter((x) => x > WIDTH).length;
    expect(screen.getByTestId("newer").textContent).toBe(`${hidden} newer ›`);
  });

  it("turns the vertical wheel sideways, and pins a chosen point scrolled out of view to its edge", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(0)} onChange={() => undefined} width={WIDTH} />);
    const wheel = new WheelEvent("wheel", { deltaX: 0, deltaY: 400, bubbles: true, cancelable: true });
    act(() => void view().dispatchEvent(wheel));
    expect(wheel.defaultPrevented).toBe(true);
    expect(offset()).toBe(400);
    fireEvent.click(screen.getByTestId("pinned-handle"));
    expect(offset()).toBe(0);
    expect(screen.queryByTestId("pinned-handle")).toBeNull();
  });

  it("leaves a sideways swipe to the browser", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(0)} onChange={() => undefined} width={WIDTH} />);
    const swipe = new WheelEvent("wheel", { deltaX: 300, deltaY: 0, bubbles: true, cancelable: true });
    act(() => void view().dispatchEvent(swipe));
    expect(swipe.defaultPrevented).toBe(false);
  });

  it("scrolls by a drag with the mouse", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(0)} onChange={() => undefined} width={WIDTH} />);
    fireEvent.pointerDown(view(), { clientX: 400, pointerType: "mouse" });
    fireEvent.pointerMove(view(), { clientX: 150, pointerType: "mouse" });
    fireEvent.pointerUp(view(), { pointerType: "mouse" });
    expect(offset()).toBe(250);
  });

  it("names only the versions' own points, by their number, and Live", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(9)} onChange={() => undefined} width={WIDTH} />);
    expect(screen.getByTestId(`label-${id(0)}`).textContent).toBe("0.0.0");
    expect(screen.queryByTestId(`label-${id(1)}`)).toBeNull();
    if (live) expect(screen.getByTestId("label-live").textContent).toBe("Live");
    for (const label of screen.queryAllByTestId(/^label-/)) expect(label.textContent).toMatch(/^(\d+\.\d+\.\d+|Live)$/);
  });
});
