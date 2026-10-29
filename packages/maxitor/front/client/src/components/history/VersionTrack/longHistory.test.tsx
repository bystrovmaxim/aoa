// src/components/history/VersionTrack/longHistory.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { MIN_STEP, VersionTrack } from "./VersionTrack";

afterEach(cleanup);

const WIDTH = 520;
const LIVE = "https://live.example";

function versions(count: number, releaseEvery = 8): HistoryVersion[] {
  return Array.from({ length: count }, (_, i) => ({
    sha: `${i}`.padStart(6, "0").padEnd(40, "e"),
    date: "2026-10-01T00:00:00Z",
    tags: i % releaseEvery === 0 ? [{ name: `v0.${i}.0`, release: { title: "", url: "" } }] : [],
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

describe.each([
  ["M2", 64, null],
  ["M4", 64, LIVE],
  ["M2", 500, null],
  ["M4", 500, LIVE],
] as const)("a long history, %s with %i versions", (_mode, count, live) => {
  it("keeps points at least 24 px apart, with no scrollbar", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(count - 1)} onChange={() => undefined} width={WIDTH} />);
    const at = xs();
    for (let i = 1; i < count; i += 1) expect(at[i] - at[i - 1]).toBeGreaterThanOrEqual(MIN_STEP);
    expect(getComputedStyle(screen.getByTestId("track")).overflow).toBe("hidden");
  });

  it("opens with the chosen version in view, and fades the side where more is hidden", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(0)} onChange={() => undefined} width={WIDTH} />);
    expect(offset()).toBe(0);
    const view = screen.getByTestId("track-view");
    expect(view.hasAttribute("data-fade-left")).toBe(false);
    expect(view.hasAttribute("data-fade-right")).toBe(true);
  });

  it("counts the newer versions out of view, and Live when it is out of view too", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(0)} onChange={() => undefined} width={WIDTH} />);
    const hidden = xs().filter((x) => x > WIDTH).length;
    expect(screen.getByTestId("newer").textContent).toBe(`${hidden} newer ›`);
  });

  it("scrolls by the wheel, sideways and vertical, and pins a handle scrolled out of view to its edge", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(0)} onChange={() => undefined} width={WIDTH} />);
    const track = screen.getByTestId("track");
    fireEvent.wheel(track, { deltaX: 300, deltaY: 0 });
    expect(offset()).toBe(300);
    fireEvent.wheel(track, { deltaX: 0, deltaY: 400 });
    expect(offset()).toBe(700);
    expect(screen.getByTestId("track-view").hasAttribute("data-fade-left")).toBe(true);
    fireEvent.click(screen.getByTestId("pinned-handle"));
    expect(offset()).toBe(0);
    expect(screen.queryByTestId("pinned-handle")).toBeNull();
  });

  it("scrolls by a drag on the track", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(0)} onChange={() => undefined} width={WIDTH} />);
    const track = screen.getByTestId("track");
    fireEvent.pointerDown(track, { clientX: 400 });
    fireEvent.pointerMove(track, { clientX: 150 });
    fireEvent.pointerUp(track);
    expect(offset()).toBe(250);
  });

  it("keeps the names of the oldest, the newest, the chosen and Live", () => {
    render(<VersionTrack versions={versions(count)} live={live} value={id(9)} onChange={() => undefined} width={WIDTH} />);
    expect(screen.getByTestId(`label-${id(0)}`)).toBeTruthy();
    expect(screen.getByTestId(`label-${id(count - 1)}`)).toBeTruthy();
    if (live) expect(screen.getByTestId("label-live")).toBeTruthy();
    expect(screen.queryAllByTestId(/^label-/).length).toBeLessThan(count);
  });
});
