// src/components/history/VersionTrack/followTip.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { clearFocus, focusToSend, putFocus, setFollowTarget } from "@/rooms/focusStore";
import { VersionTrack } from "./VersionTrack";

afterEach(() => {
  cleanup();
  clearFocus();
});

function version(n: number): HistoryVersion {
  return { sha: `${n}`.padEnd(40, "b"), date: "2026-10-01T00:00:00Z", tags: [], nodes: 1, edges: 1, source: `s${n}`, pr: { number: n, title: `Change ${n}`, body: "", url: "" } };
}
const id = (n: number) => `${n}`.padEnd(12, "b");
const PAGE = "view=domain-erd";

function drawTrack() {
  render(<VersionTrack versions={[version(1), version(2), version(3)]} live={null} value={id(3)} onChange={() => undefined} width={400} />);
}

describe("a version's tooltip in a room (spec 038)", () => {
  it("is reported as your hover, so the people who follow you see it", () => {
    drawTrack();
    const point = screen.getByTestId(`point-${id(2)}`);
    const axis = Number(point.querySelector("circle")?.getAttribute("cy") ?? point.getAttribute("cy"));
    fireEvent.pointerMove(screen.getByTestId("track-view"), { clientX: Number(point.getAttribute("data-x")), clientY: axis, pointerType: "mouse" });
    expect(screen.getByTestId("version-tip").textContent).toContain("Change 2");
    expect(focusToSend(PAGE).hover).toEqual({ kind: "version", id: id(2) });
  });

  it("shows for a follower the version the person they follow has under the pointer", () => {
    putFocus("anna", { page: PAGE, hover: { kind: "version", id: id(1) }, tooltip: { kind: "version", id: id(1) }, selection: null, panels: { sidebar: [], filter: null, legend: false, versions: true } });
    setFollowTarget("anna");
    drawTrack();
    expect(screen.getByTestId("version-tip").textContent).toContain("Change 1");
  });
});
