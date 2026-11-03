// src/components/history/VersionTrack/oneDrag.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { VersionTrack } from "./VersionTrack";

afterEach(cleanup);

function version(n: number): HistoryVersion {
  return { sha: `${n}`.padEnd(40, "d"), date: "2026-10-01T00:00:00Z", tags: [], nodes: 1, edges: 1, source: `s${n}`, pr: { number: n, title: "", body: "", url: "" } };
}
const id = (n: number) => `${n}`.padEnd(12, "d");
const FOUR = [version(1), version(2), version(3), version(4)];

function track(value: string) {
  const onChange = vi.fn();
  render(<VersionTrack versions={FOUR} live={null} value={value} onChange={onChange} width={500} />);
  const x = (b: string) => Number(screen.getByTestId(`point-${b}`).getAttribute("data-x"));
  const knobX = () => Number(screen.getByTestId("handle").querySelector("circle")?.getAttribute("cx"));
  return { onChange, x, knobX, handle: () => screen.getByTestId("handle") };
}

describe("the handle of One", () => {
  it("is dragged from point to point and chosen where it is let go, as a handle of Diff", () => {
    const { onChange, x, knobX, handle } = track(id(1));
    fireEvent.pointerDown(handle(), { clientX: x(id(1)), pointerId: 1 });
    fireEvent.pointerMove(handle(), { clientX: x(id(2)) + 3, pointerId: 1 });
    fireEvent.pointerMove(handle(), { clientX: x(id(3)) - 2, pointerId: 1 });
    // While it is dragged it stands on the point it would be let go on, and nothing is chosen yet.
    expect(knobX()).toBe(x(id(3)));
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.pointerUp(handle(), { clientX: x(id(3)), pointerId: 1 });
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith(id(3));
  });

  it("chooses nothing when it is let go where it stood", () => {
    const { onChange, x, handle } = track(id(2));
    fireEvent.pointerDown(handle(), { clientX: x(id(2)), pointerId: 1 });
    fireEvent.pointerMove(handle(), { clientX: x(id(2)) + 2, pointerId: 1 });
    fireEvent.pointerUp(handle(), { clientX: x(id(2)) + 2, pointerId: 1 });
    expect(onChange).not.toHaveBeenCalled();
  });
});
