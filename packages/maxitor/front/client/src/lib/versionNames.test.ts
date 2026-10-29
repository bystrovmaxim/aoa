// src/lib/versionNames.test.ts
import { describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { defaultVersion, flagsOf, nameOf, tooltipOf, versionNames } from "./versionNames";

function version(n: number, extra: Partial<HistoryVersion> = {}): HistoryVersion {
  return { sha: `${n}`.padEnd(40, "a"), date: `2026-10-${String(n).padStart(2, "0")}T00:00:00Z`, tags: [], nodes: n * 10, edges: n * 20, source: `s${n}`, ...extra };
}

const pr = (n: number) => ({ pr: { number: n, title: `Change ${n}`, body: "", url: "" } });
const release = (name: string) => ({ tags: [{ name, release: { title: name, url: "" } }] });

describe("names on the track (R10)", () => {
  const versions = [version(1, pr(10)), version(2, { message: "Direct" }), version(3, { ...pr(12), ...release("v0.1.0") }), version(4, pr(14)), version(5, { ...pr(16), tags: [{ name: "prod", release: null }] })];

  it("names a version before any release by its pull request or short commit, a release by its tag, the rest after it", () => {
    expect(versionNames(versions)).toEqual(["#10", "2aaaaaa", "v0.1.0", "v0.1.0 · #14", "v0.1.0 · #16"]);
  });

  it("names a version a short sha or live names", () => {
    expect(nameOf(versions, versions[3].sha.slice(0, 12))).toBe("v0.1.0 · #14");
    expect(nameOf(versions, "live")).toBe("Live");
    expect(nameOf(versions, "f".repeat(12))).toBeNull();
  });

  it("keeps a tag without a release as a flag", () => {
    expect(flagsOf(versions[4])).toEqual(["prod"]);
  });

  it("ends a refused version's tooltip with its reason", () => {
    expect(tooltipOf(version(6, { ...pr(18), refused: "bad graph" })).split("\n")).toEqual(["#18 Change 18", "2026-10-06", "60 nodes · 120 edges", "refused: bad graph"]);
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
