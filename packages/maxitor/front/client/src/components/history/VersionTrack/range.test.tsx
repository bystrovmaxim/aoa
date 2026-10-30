// src/components/history/VersionTrack/range.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { HistoryVersion } from "@/api/history";
import type { Range } from "@/lib/versionRange";
import { VersionTrack } from "./VersionTrack";

afterEach(cleanup);

function version(n: number): HistoryVersion {
  return { sha: `${n}`.padEnd(40, "d"), date: "2026-10-01T00:00:00Z", tags: [], nodes: 1, edges: 1, source: `s${n}`, pr: { number: n, title: "", body: "", url: "" } };
}
const id = (n: number) => `${n}`.padEnd(12, "d");
const LIVE = "https://live.example";
const FOUR = [version(1), version(2), version(3), version(4)];

function track(range: Range, live: string | null = LIVE) {
  const onRange = vi.fn();
  const view = render(<VersionTrack versions={FOUR} live={live} value={range.b} onChange={vi.fn()} range={range} onRange={onRange} width={500} />);
  const x = (b: string) => Number(screen.getByTestId(`point-${b}`).getAttribute("data-x"));
  return { onRange, x, view, a: () => screen.getByTestId("handle-a"), b: () => screen.getByTestId("handle-b") };
}

describe("two handles on one track", () => {
  it("draw A and B, the stretch between them dark, each a slider named by its role", () => {
    const { a, b } = track({ a: id(2), b: id(3) });
    expect(screen.getByTestId("range-stretch")).toBeTruthy();
    expect(a().getAttribute("aria-valuetext")).toBe("A, #2, older version");
    expect(b().getAttribute("aria-valuetext")).toBe("B, #3, newer version");
    expect(screen.queryByTestId("handle")).toBeNull();
    expect(screen.getByTestId("track").getAttribute("role")).toBe("group");
  });

  it("swap roles when one is dragged past the other", () => {
    const { a, x, onRange } = track({ a: id(1), b: id(2) });
    fireEvent.pointerDown(a(), { clientX: x(id(1)), pointerId: 1 });
    fireEvent.pointerMove(a(), { clientX: x(id(2)) + 5, pointerId: 1 });
    fireEvent.pointerMove(a(), { clientX: x(id(4)), pointerId: 1 });
    fireEvent.pointerUp(a(), { clientX: x(id(4)), pointerId: 1 });
    expect(onRange).toHaveBeenCalledWith({ a: id(2), b: id(4) });
  });

  it("never stand on one point: dropped on the other, a handle goes one further in its direction", () => {
    const { b, x, onRange } = track({ a: id(2), b: id(4) });
    fireEvent.pointerDown(b(), { clientX: x(id(4)), pointerId: 1 });
    fireEvent.pointerMove(b(), { clientX: x(id(3)), pointerId: 1 });
    fireEvent.pointerMove(b(), { clientX: x(id(2)), pointerId: 1 });
    fireEvent.pointerUp(b(), { clientX: x(id(2)), pointerId: 1 });
    expect(onRange).toHaveBeenCalledWith({ a: id(1), b: id(2) });
  });

  it("make Live only B", () => {
    const { a, x, onRange } = track({ a: id(3), b: id(4) });
    fireEvent.pointerDown(a(), { clientX: x(id(3)), pointerId: 1 });
    fireEvent.pointerMove(a(), { clientX: x("live"), pointerId: 1 });
    fireEvent.pointerUp(a(), { clientX: x("live"), pointerId: 1 });
    expect(onRange).toHaveBeenCalledWith({ a: id(4), b: "live" });
  });

  it("step with ← →, past the other too, and the moved handle keeps the focus", () => {
    const { a, onRange, view } = track({ a: id(2), b: id(3) });
    a().focus();
    fireEvent.keyDown(a(), { key: "ArrowRight" });
    expect(onRange).toHaveBeenLastCalledWith({ a: id(3), b: id(4) });
    view.rerender(<VersionTrack versions={FOUR} live={LIVE} value={id(4)} onChange={vi.fn()} range={{ a: id(3), b: id(4) }} onRange={onRange} width={500} />);
    expect(document.activeElement).toBe(screen.getByTestId("handle-b"));
  });

  it("move both with Shift + ← →, keeping the distance, and stop at the end", () => {
    const { b, onRange, view } = track({ a: id(2), b: id(3) });
    fireEvent.keyDown(b(), { key: "ArrowRight", shiftKey: true });
    expect(onRange).toHaveBeenLastCalledWith({ a: id(3), b: id(4) });
    view.rerender(<VersionTrack versions={FOUR} live={LIVE} value="live" onChange={vi.fn()} range={{ a: id(4), b: "live" }} onRange={onRange} width={500} />);
    fireEvent.keyDown(screen.getByTestId("handle-b"), { key: "ArrowRight", shiftKey: true });
    expect(onRange).toHaveBeenCalledTimes(1);
  });

  it("take the focused handle to the ends with Home and End", () => {
    const { b, onRange } = track({ a: id(2), b: id(3) });
    fireEvent.keyDown(b(), { key: "End" });
    expect(onRange).toHaveBeenLastCalledWith({ a: id(2), b: "live" });
    fireEvent.keyDown(b(), { key: "Home" });
    expect(onRange).toHaveBeenLastCalledWith({ a: id(1), b: id(2) });
  });

  it("move the nearer handle to a clicked point", () => {
    const { onRange } = track({ a: id(2), b: id(3) });
    fireEvent.click(screen.getByTestId("point-live"));
    expect(onRange).toHaveBeenLastCalledWith({ a: id(2), b: "live" });
    fireEvent.click(screen.getByTestId(`point-${id(1)}`));
    expect(onRange).toHaveBeenLastCalledWith({ a: id(1), b: id(3) });
  });
});
