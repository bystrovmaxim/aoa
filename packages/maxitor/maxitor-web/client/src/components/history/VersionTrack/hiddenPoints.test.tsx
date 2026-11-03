// src/components/history/VersionTrack/hiddenPoints.test.tsx
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { layOut, VersionTrack } from "./VersionTrack";

afterEach(cleanup);

/** Version ``n``: it changed the graph unless ``small``, at number ``number``. */
function version(n: number, small: boolean, number: string | null, changed: boolean, tags: HistoryVersion["tags"] = []): HistoryVersion {
  return { sha: `${n}`.padStart(4, "0").padEnd(40, "a"), date: "2026-10-01T00:00:00Z", tags, nodes: 1, edges: 1, source: `s${n}`, graph_changed: !small, version: number, version_changed: changed };
}

const id = (v: HistoryVersion) => v.sha.slice(0, 12);
const RELEASED = [{ name: "release-1", release: { title: "Release 1", url: "https://r" } }];
const ALL = [version(1, false, "1.0.0", true), version(2, true, "1.1.0", true, RELEASED), version(3, false, "1.1.0", false), version(4, true, "1.2.0", true)];
const LOOK = { versionFile: true, hideSmall: true };

describe("points by what changed (spec 051)", () => {
  it("draws a large point where the graph changed and a small one where it did not", () => {
    render(<VersionTrack versions={ALL} live={null} value={null} onChange={() => undefined} width={700} versionFile />);
    const size = (v: HistoryVersion) => screen.getByTestId(`point-${id(v)}`).querySelector("[data-size]")?.getAttribute("data-size");
    expect(ALL.map(size)).toEqual(["large", "small", "large", "small"]);
  });

  it("writes a number only where it changed", () => {
    const { points } = layOut(ALL, null, 700, 24, null, [], { versionFile: true });
    expect(points.map((point) => point.named)).toEqual([true, true, false, true]);
    expect(points.map((point) => point.number)).toEqual(["1.0.0", "1.1.0", "1.1.0", "1.2.0"]);
  });

  it("writes none for a point whose version is empty", () => {
    const { points } = layOut([version(1, false, null, false)], null, 700, 24, null, [], { versionFile: true });
    expect([points[0].named, points[0].number]).toEqual([false, null]);
  });

  it("counts a point with no word on the graph as a change, and takes numbers from tags with no file", () => {
    const old: HistoryVersion = { sha: "9".repeat(40), date: "2026-10-01T00:00:00Z", tags: [{ name: "v2.0.0", release: null }], nodes: 1, edges: 1, source: "s" };
    const { points } = layOut([old], null, 700);
    expect([points[0].large, points[0].named, points[0].number]).toEqual([true, true, "2.0.0"]);
  });
});

describe("hiding points (spec 051)", () => {
  it("leaves out only the small points, and renames nothing", () => {
    const { points } = layOut(ALL, null, 700, 24, null, [], LOOK);
    expect(points.map((point) => point.b)).toEqual([id(ALL[0]), id(ALL[2])]);
    expect(points.map((point) => point.name)).toEqual(["#1", "#3"]);
  });

  it("keeps a chosen small point, also when it is an end of a range or a followed drag", () => {
    const { points } = layOut(ALL, null, 700, 24, null, [], { ...LOOK, kept: new Set([id(ALL[1])]) });
    expect(points.map((point) => point.b)).toContain(id(ALL[1]));
  });

  it("does not call for a new choice when points hide", () => {
    let calls = 0;
    const onChange = () => void (calls += 1);
    const { rerender } = render(<VersionTrack versions={ALL} live={null} value={id(ALL[1])} onChange={onChange} width={700} versionFile />);
    rerender(<VersionTrack versions={ALL} live={null} value={id(ALL[1])} onChange={onChange} width={700} versionFile hideSmall />);
    expect(calls).toBe(0);
    expect(screen.getByTestId(`point-${id(ALL[1])}`)).toBeTruthy();
    rerender(<VersionTrack versions={ALL} live={null} value={id(ALL[0])} onChange={onChange} width={700} versionFile hideSmall />);
    expect(screen.queryByTestId(`point-${id(ALL[1])}`)).toBeNull();
  });

  it("keeps both ends of a range", () => {
    render(<VersionTrack versions={ALL} live={null} value={null} onChange={() => undefined} width={700} versionFile hideSmall range={{ a: id(ALL[1]), b: id(ALL[3]) }} onRange={() => undefined} />);
    expect(screen.getByTestId(`point-${id(ALL[1])}`)).toBeTruthy();
    expect(screen.getByTestId(`point-${id(ALL[3])}`)).toBeTruthy();
  });

  it("draws a hidden point's flags on the nearest drawn point before it", () => {
    const { points } = layOut(ALL, null, 700, 24, null, [], LOOK);
    expect(points[0].carried).toEqual(["release-1"]);
    expect(points[1].carried).toEqual([]);
  });

  it("gives them to the earliest drawn point when none stands before", () => {
    const history = [version(1, true, "1.0.0", true, RELEASED), version(2, false, "1.0.0", false)];
    expect(layOut(history, null, 700, 24, null, [], LOOK).points[0].carried).toEqual(["release-1"]);
  });
});
