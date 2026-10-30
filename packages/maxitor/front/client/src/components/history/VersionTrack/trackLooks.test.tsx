// src/components/history/VersionTrack/trackLooks.test.tsx
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { HistoryVersion, ProposalState } from "@/api/history";
import { DIRECT_LOOK, LIVE_LOOK, MERGED_LOOK, PROPOSAL_LOOK } from "./proposalLook";
import { VersionTrack } from "./VersionTrack";

afterEach(cleanup);

const LIVE = "https://live.example";

/** Version ``n``: merged as pull request ``n`` when ``merged``, else pushed straight; tags as given. */
function version(n: number, merged: boolean, tags: HistoryVersion["tags"] = []): HistoryVersion {
  return {
    sha: `${n}`.padStart(4, "0").padEnd(40, "a"),
    date: `2026-10-${String(n).padStart(2, "0")}T00:00:00Z`,
    tags,
    nodes: 1,
    edges: 1,
    source: `s${n}`,
    ...(merged ? { pr: { number: 100 + n, title: `Change ${n}`, body: "", url: "" } } : { message: `Push ${n}` }),
  };
}

function proposal(n: number, state: ProposalState): HistoryVersion {
  return { sha: `f${n}`.padEnd(40, "b"), date: "2026-10-20T00:00:00Z", tags: [], nodes: 1, edges: 1, source: `p${n}`, pr: { number: 200 + n, title: `Proposal ${n}`, body: "", url: "", state } };
}

const id = (v: HistoryVersion) => v.sha.slice(0, 12);
/** The visible circle of a point: the one after its hit target. */
const dot = (b: string) => screen.getByTestId(`point-${b}`).querySelectorAll("circle")[1];
/** The stretch of line that leads to point ``b``. */
const line = (container: HTMLElement, x: string) => container.querySelector(`line[x2="${x}"]`);

const history = [version(1, false, [{ name: "v0.1.0", release: null }]), version(2, false), version(3, true, [{ name: "v0.2.0", release: null }, { name: "release-0.2", release: null }]), version(4, true, [{ name: "prod", release: null }])];

describe("one colour per kind of point (FR-037)", () => {
  it("draws a direct push grey, a merged pull request purple, Live hollow grey", () => {
    render(<VersionTrack versions={history} live={LIVE} value={null} onChange={() => undefined} width={700} />);
    expect(dot(id(history[1])).getAttribute("fill")).toBe(DIRECT_LOOK.colour);
    expect(dot(id(history[3])).getAttribute("fill")).toBe(MERGED_LOOK.colour);
    expect(dot("live").getAttribute("fill")).toBe("#fff");
    expect(dot("live").getAttribute("stroke")).toBe(LIVE_LOOK.colour);
  });

  it("colours each stretch of line by the point it leads to: solid to a version, dashed to what is not in the history yet", () => {
    const { container } = render(<VersionTrack versions={history} live={LIVE} proposals={[proposal(1, "approved")]} value={null} onChange={() => undefined} width={700} />);
    const toMerged = line(container, screen.getByTestId(`point-${id(history[2])}`).getAttribute("data-x")!);
    expect(toMerged?.getAttribute("stroke")).toBe(MERGED_LOOK.colour);
    expect(toMerged?.getAttribute("stroke-dasharray")).toBeNull();
    const toProposal = screen.getByTestId("proposals-gap");
    expect(toProposal.getAttribute("stroke")).toBe(PROPOSAL_LOOK.approved.colour);
    expect(toProposal.getAttribute("stroke-dasharray")).toBe("2 4");
    expect(screen.getByTestId("live-gap").getAttribute("stroke-dasharray")).toBe("2 4");
  });

  it("keeps the chosen point's kind on its chip", () => {
    render(<VersionTrack versions={history} live={LIVE} proposals={[proposal(1, "changes_requested")]} value={id(proposal(1, "changes_requested"))} onChange={() => undefined} width={700} />);
    const chip = screen.getByTestId("chip");
    expect(chip.querySelector("rect")?.getAttribute("fill")).toBe(PROPOSAL_LOOK.changes_requested.colour);
    expect(chip.textContent).toBe("#201");
  });

  it("writes a version before the chosen point's name where there is one", () => {
    render(<VersionTrack versions={history} live={null} value={id(history[3])} onChange={() => undefined} width={700} />);
    expect(screen.getByTestId("chip").textContent).toBe("0.2.0 · #104");
  });
});

describe("open pull requests and Live (FR-036, FR-037)", () => {
  it("stands open pull requests after the history and before Live, which is always last", () => {
    render(<VersionTrack versions={history} live={LIVE} proposals={[proposal(1, "open"), proposal(2, "approved")]} value={null} onChange={() => undefined} width={700} />);
    const x = (b: string) => Number(screen.getByTestId(`point-${b}`).getAttribute("data-x"));
    expect(x(id(proposal(1, "open")))).toBeGreaterThan(x(id(history[3])));
    expect(x(id(proposal(2, "approved")))).toBeGreaterThan(x(id(proposal(1, "open"))));
    expect(x("live")).toBeGreaterThan(x(id(proposal(2, "approved"))));
  });

  it("draws Live and the newest version as one point when Live runs exactly its graph", () => {
    render(<VersionTrack versions={history} live={LIVE} liveIs={history[3].sha} value="live" onChange={() => undefined} width={700} />);
    expect(screen.queryByTestId(`point-${id(history[3])}`)).toBeNull();
    expect(screen.getByTestId("point-live")).toBeTruthy();
    expect(screen.getByTestId("chip").textContent).toBe("Live");
  });
});

describe("names and flags (FR-017, FR-033)", () => {
  it("names only a version's own point, by its number, and Live", () => {
    render(<VersionTrack versions={history} live={LIVE} value={null} onChange={() => undefined} width={700} />);
    expect(screen.getByTestId(`label-${id(history[0])}`).textContent).toBe("0.1.0");
    expect(screen.queryByTestId(`label-${id(history[1])}`)).toBeNull();
    expect(screen.getByTestId(`label-${id(history[2])}`).textContent).toBe("0.2.0");
    expect(screen.queryByTestId(`label-${id(history[3])}`)).toBeNull();
    expect(screen.getByTestId("label-live").textContent).toBe("Live");
  });

  it("names nothing but Live in a history with no version tags", () => {
    render(<VersionTrack versions={[version(1, true), version(2, false)]} live={LIVE} value={null} onChange={() => undefined} width={700} />);
    expect(screen.queryAllByTestId(/^label-/).map((label) => label.textContent)).toEqual(["Live"]);
  });

  it("flags only a release", () => {
    render(<VersionTrack versions={history} live={null} value={null} onChange={() => undefined} width={700} />);
    expect(screen.queryAllByTestId(/^flag-/).map((flag) => flag.getAttribute("data-testid"))).toEqual([`flag-${id(history[2])}`]);
  });
});
