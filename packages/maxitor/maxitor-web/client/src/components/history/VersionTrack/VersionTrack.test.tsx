// src/components/history/VersionTrack/VersionTrack.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { VersionTrack } from "./VersionTrack";

afterEach(cleanup);

function version(n: number, extra: Partial<HistoryVersion> = {}): HistoryVersion {
  return { sha: `${n}`.padEnd(40, "b"), date: "2026-10-01T00:00:00Z", tags: [], nodes: 1, edges: 1, source: `s${n}`, pr: { number: n, title: "", body: "", url: "" }, ...extra };
}
const id = (n: number) => `${n}`.padEnd(12, "b");
const LIVE = "https://live.example";

function track(versions: HistoryVersion[], live: string | null, value: string | null) {
  const onChange = vi.fn();
  render(<VersionTrack versions={versions} live={live} value={value} onChange={onChange} width={400} />);
  return { onChange, slider: screen.getByRole("slider") };
}

describe("the track", () => {
  it("draws a point per version, Live after a dashed gap, a refused version hollow", () => {
    track([version(1), version(2, { refused: "x" }), version(3)], LIVE, "live");
    expect(screen.getAllByTestId(/^point-/)).toHaveLength(4);
    expect(screen.getByTestId("live-gap")).toBeTruthy();
    expect(screen.getByTestId(`point-${id(2)}`).getAttribute("data-refused")).toBe("true");
  });

  it("has no dashed gap without Live", () => {
    track([version(1), version(2)], null, id(2));
    expect(screen.queryByTestId("live-gap")).toBeNull();
  });

  it("steps with ← →, and Home and End jump to the ends (M4)", () => {
    const { onChange, slider } = track([version(1), version(2), version(3)], LIVE, id(2));
    expect(slider.getAttribute("aria-valuetext")).toBe("#2");
    for (const key of ["ArrowLeft", "ArrowRight", "Home", "End"]) fireEvent.keyDown(slider, { key });
    expect(onChange.mock.calls.map((call) => call[0])).toEqual([id(1), id(3), id(1), "live"]);
  });

  it("does nothing with the keys where there is nothing to step to (M3, M6)", () => {
    for (const [versions, live, value] of [[[version(1)], null, id(1)], [[], LIVE, "live"]] as const) {
      const { onChange, slider } = track([...versions], live, value);
      for (const key of ["ArrowLeft", "ArrowRight", "Home", "End"]) fireEvent.keyDown(slider, { key });
      expect(onChange).not.toHaveBeenCalled();
      cleanup();
    }
  });

  it("moves between the one point and Live (M5)", () => {
    const { onChange, slider } = track([version(1)], LIVE, "live");
    fireEvent.keyDown(slider, { key: "Home" });
    expect(onChange).toHaveBeenCalledWith(id(1));
  });

  it("chooses a version by a click on its point", () => {
    const { onChange } = track([version(1), version(2)], null, id(2));
    fireEvent.click(screen.getByTestId(`point-${id(1)}`));
    expect(onChange).toHaveBeenCalledWith(id(1));
  });
});
