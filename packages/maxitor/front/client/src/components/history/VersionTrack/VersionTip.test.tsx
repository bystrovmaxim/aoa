// src/components/history/VersionTrack/VersionTip.test.tsx
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { changeOf, initialsOf, kindCount, VersionTip, whenOf } from "./VersionTip";

afterEach(cleanup);

function version(extra: Partial<HistoryVersion> = {}): HistoryVersion {
  return { sha: "a".repeat(40), date: "2026-10-29T10:00:00Z", tags: [], nodes: 1, edges: 1, source: "s", ...extra };
}

const merged = version({
  pr: { number: 147, title: "Offer regions", body: "", url: "", author: "anna", avatar: "" },
  contribution: { author: "Anna Petrova", co_authors: 1, merged_by: "Maxim Bystrov", files: 2, additions: 21, deletions: 1 },
  change: { added: { Entity: 1, EntityField: 4 }, removed: { Field: 1 }, changed: 2, links: { added: 3, removed: 1 } },
});

describe("what a point's card says, in words", () => {
  it("says when, near or in full", () => {
    const now = Date.parse("2026-10-30T12:00:00Z");
    expect(whenOf("2026-10-30T11:40:00Z", now)).toBe("20 min ago");
    expect(whenOf("2026-10-30T09:00:00Z", now)).toBe("3 h ago");
    expect(whenOf("2026-10-27T12:00:00Z", now)).toBe("3 days ago");
    expect(whenOf("2026-11-06T12:00:00Z", now)).toMatch(/^Nov 6, 2026$/);
  });

  it("counts a graph's kinds in plain words", () => {
    expect(kindCount("Entity", 1)).toBe("1 entity");
    expect(kindCount("Entity", 2)).toBe("2 entities");
    expect(kindCount("EntityField", 4)).toBe("4 entity fields");
  });

  it("tells what a version did to the graph: nodes by kind, nodes changed, links", () => {
    expect(changeOf(merged.change)).toEqual(["+1 entity", "+4 entity fields", "−1 field", "2 changed", "+3 links", "−1 link"]);
    expect(changeOf(undefined)).toEqual([]);
  });

  it("gives a person with no picture two letters", () => {
    expect(initialsOf("Anna Petrova")).toBe("AP");
    expect(initialsOf("olga")).toBe("O");
  });
});

describe("a point's card", () => {
  it("reads as a pull request card: merged, its version, its number, title, who made and merged it, size and change", () => {
    render(<VersionTip version={merged} release="0.11.0" />);
    expect(screen.getByText("Merged")).toBeTruthy();
    expect(screen.getByText("0.11.0")).toBeTruthy();
    expect(screen.getByText("#147")).toBeTruthy();
    expect(screen.getByText("Offer regions")).toBeTruthy();
    expect(screen.getByText("anna")).toBeTruthy();
    expect(screen.getByText("Maxim Bystrov")).toBeTruthy();
    expect(screen.getByText("+1")).toBeTruthy();
    expect(screen.getByText("2 files")).toBeTruthy();
    expect(screen.getByText(/\+3 links/)).toBeTruthy();
  });

  it("says Direct push for a change with no pull request, and shows no version chip where there is none", () => {
    render(<VersionTip version={version({ message: "Fix the seed\n\nmore", contribution: { author: "Ivan", co_authors: 0, merged_by: null, files: 1, additions: 2, deletions: 0 } })} release={null} />);
    expect(screen.getByText("Direct push")).toBeTruthy();
    expect(screen.queryByText("Merged")).toBeNull();
    expect(screen.getByText("Fix the seed")).toBeTruthy();
  });

  it("says an open pull request's state instead of Merged", () => {
    render(<VersionTip version={version({ pr: { number: 158, title: "Bundles", body: "", url: "", state: "approved" } })} release={null} state="approved" />);
    expect(screen.getByText("Approved")).toBeTruthy();
    expect(screen.queryByText("Merged")).toBeNull();
  });

  it("marks a release with its title, and lists the other tags", () => {
    render(<VersionTip version={version({ pr: { number: 1, title: "T", body: "", url: "" }, tags: [{ name: "v1.0.0", release: { title: "Spring", url: "u" } }, { name: "prod", release: null }] })} release="1.0.0" />);
    expect(screen.getByText("Release")).toBeTruthy();
    expect(screen.getByText("Spring")).toBeTruthy();
    expect(screen.getByText("tags: prod")).toBeTruthy();
  });

  it("marks Live, carrying the version it runs when they are one", () => {
    render(<VersionTip version={merged} release="0.11.0" live />);
    expect(screen.getByText("Live")).toBeTruthy();
    expect(screen.getByText("Offer regions")).toBeTruthy();
  });
});
