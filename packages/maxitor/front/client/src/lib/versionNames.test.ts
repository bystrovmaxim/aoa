// src/lib/versionNames.test.ts
import { describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { defaultVersion, flagsOf, nameOf, tipOf, versionNames } from "./versionNames";

function version(n: number, extra: Partial<HistoryVersion> = {}): HistoryVersion {
  return { sha: `${n}`.padEnd(40, "a"), date: `2026-10-${String(n).padStart(2, "0")}T00:00:00Z`, tags: [], nodes: n * 10, edges: n * 20, source: `s${n}`, ...extra };
}

const pr = (n: number) => ({ pr: { number: n, title: `Change ${n}`, body: "", url: "" } });
const release = (name: string) => ({ tags: [{ name, release: { title: name, url: "" } }] });

describe("names on the track (R10)", () => {
  const versions = [version(1, pr(10)), version(2, { date: new Date(2026, 9, 2, 12).toISOString(), message: "Direct" }), version(3, { ...pr(12), ...release("v0.1.0") }), version(4, pr(14)), version(5, { ...pr(16), tags: [{ name: "prod", release: null }] })];

  it("names a version before any release by its pull request or its place, a release by its tag without the v, the rest after it", () => {
    expect(versionNames(versions)).toEqual(["#10", "#2", "0.1.0", "0.1.0 · #14", "0.1.0 · #16"]);
  });

  it("never names a direct commit by its hash, but by its place in the history, the oldest being 1", () => {
    const names = versionNames([version(1, { message: "First" }), version(2, { ...pr(2), ...release("v1.0.0") }), version(3, { message: "Direct" }), version(4, pr(9)), version(5, { message: "Direct" })]);
    expect(names).toEqual(["#1", "1.0.0", "1.0.0 · #3", "1.0.0 · #9", "1.0.0 · #5"]);
  });

  it("names a version a short sha or live names", () => {
    expect(nameOf(versions, versions[3].sha.slice(0, 12))).toBe("0.1.0 · #14");
    expect(nameOf(versions, "live")).toBe("Live");
    expect(nameOf(versions, "f".repeat(12))).toBeNull();
  });

  it("draws every tag as a flag", () => {
    expect(flagsOf(versions[4])).toEqual(["prod"]);
  });

  it("takes a tag that is a version number for a release even with no release on the host", () => {
    const local = [version(1, { tags: [{ name: "v0.8.0", release: null }] }), version(2, pr(20)), version(3, { date: new Date(2026, 9, 3, 12).toISOString(), tags: [{ name: "prod", release: null }] })];
    expect(versionNames(local)).toEqual(["0.8.0", "0.8.0 · #20", "0.8.0 · #3"]);
    expect(flagsOf(local[0])).toEqual(["v0.8.0"]);
    expect(flagsOf(local[2])).toEqual(["prod"]);
  });

  it("tells in a tooltip the commit, how it came, the date and tags, the title, the size and the pull request, and why it was refused", () => {
    const tip = tipOf(version(6, { ...pr(18), date: new Date(2026, 9, 6, 12).toISOString(), tags: [{ name: "v0.9.0", release: null }], refused: "bad graph" }));
    expect(tip).toEqual({ commit: "6aaaaaa", kind: "pull request", when: "Oct 6, 2026 · tag v0.9.0", title: "Change 18", size: "60 nodes · 120 edges · #18", refused: "bad graph" });
  });
});

describe("the version a history opens on (FR-021)", () => {
  it("is Live when there is Live, else the newest unrefused, else the newest, else none", () => {
    expect(defaultVersion([version(1)], "https://live")).toBe("live");
    expect(defaultVersion([version(1), version(2, { refused: "x" })], null)).toBe(version(1).sha.slice(0, 12));
    expect(defaultVersion([version(1, { refused: "x" }), version(2, { refused: "y" })], null)).toBe(version(2).sha.slice(0, 12));
    expect(defaultVersion([], null)).toBeNull();
    expect(defaultVersion([], "https://live")).toBe("live");
  });
});
