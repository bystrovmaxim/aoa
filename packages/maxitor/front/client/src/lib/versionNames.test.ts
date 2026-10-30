// src/lib/versionNames.test.ts
import { describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { defaultVersion, flagsOf, numbersOf, releaseNoteOf, releaseOf, shownNameOf, versionNames } from "./versionNames";

function version(n: number, extra: Partial<HistoryVersion> = {}): HistoryVersion {
  return { sha: `${n}`.padEnd(40, "a"), date: `2026-10-${String(n).padStart(2, "0")}T00:00:00Z`, tags: [], nodes: n * 10, edges: n * 20, source: `s${n}`, ...extra };
}

const pr = (n: number) => ({ pr: { number: n, title: `Change ${n}`, body: "", url: "" } });

describe("names on the track (R10, FR-018)", () => {
  const versions = [
    version(1, pr(10)),
    version(2, { message: "Direct" }),
    version(3, { ...pr(12), tags: [{ name: "v0.1.0", release: null }] }),
    version(4, pr(14)),
    version(5, { ...pr(16), tags: [{ name: "prod", release: null }] }),
  ];

  it("names a version by its pull request, or by its place when it had none — never by a version or a hash", () => {
    expect(versionNames(versions)).toEqual(["#10", "#2", "#12", "#14", "#16"]);
  });

  it("gives each version the last version number at or before it, none before the first", () => {
    expect(numbersOf(versions)).toEqual([null, null, "0.1.0", "0.1.0", "0.1.0"]);
  });

  it("writes the version button's name with the version before it where there is one", () => {
    expect(shownNameOf(versions, versions[3].sha.slice(0, 12))).toBe("0.1.0 · #14");
    expect(shownNameOf(versions, versions[1].sha.slice(0, 12))).toBe("#2");
    expect(shownNameOf(versions, "live")).toBe("Live");
    const open = { ...version(9, pr(30)), sha: "f".repeat(40) };
    expect(shownNameOf(versions, "f".repeat(12), [open])).toBe("#30");
    expect(shownNameOf(versions, "e".repeat(12))).toBeNull();
  });

  it("takes only a version-number tag as a version, with or without its v", () => {
    expect(releaseOf(version(1, { tags: [{ name: "prod", release: null }, { name: "1.2.3", release: null }] }))).toBe("1.2.3");
    expect(releaseOf(version(1, { tags: [{ name: "release-4", release: null }] }))).toBeNull();
  });

  it("flags a release: a GitHub Release, or a tag named release…; any other tag is no flag", () => {
    const published = version(1, { tags: [{ name: "v1.0.0", release: { title: "Spring", url: "https://r" } }, { name: "prod", release: null }] });
    expect(flagsOf(published)).toEqual(["v1.0.0"]);
    expect(releaseNoteOf(published)).toEqual({ title: "Spring", url: "https://r" });
    const tagged = version(2, { tags: [{ name: "release/2026-10-30", release: null }] });
    expect(flagsOf(tagged)).toEqual(["release/2026-10-30"]);
    expect(releaseNoteOf(tagged)).toEqual({ title: "release/2026-10-30", url: "" });
    expect(flagsOf(versions[4])).toEqual([]);
    expect(flagsOf(versions[2])).toEqual([]);
    expect(releaseNoteOf(versions[4])).toBeNull();
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
