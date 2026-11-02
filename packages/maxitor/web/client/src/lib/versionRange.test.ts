// src/lib/versionRange.test.ts
import { describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { layOut } from "@/components/history/VersionTrack/VersionTrack";
import { shortSha } from "@/lib/versionNames";
import { afterListChange, diffOffered, homeEnd, moveTo, normalise, oneToDiff, proposalsByDate, shiftBoth, shiftBy, stepHandle, stepShown, trackKeys, type Range } from "./versionRange";

const P = ["v1", "v2", "v3", "v4", "live"];

function version(n: number, extra: Partial<HistoryVersion> = {}): HistoryVersion {
  return { sha: `${n}`.padEnd(40, "c"), date: "2026-10-01T00:00:00Z", tags: [], nodes: 1, edges: 1, source: `s${n}`, pr: { number: n, title: "", body: "", url: "" }, ...extra };
}

describe("the track's points", () => {
  it("are in the order the track draws them, the newest merged into Live when they are one", () => {
    const versions = [version(1), version(2), version(3)];
    const proposals = [version(9)];
    for (const liveIs of [null, versions[2].sha]) {
      const drawn = layOut(versions, "https://live", 600, 24, liveIs, proposals).points.map((point) => point.b);
      expect(trackKeys(versions, "https://live", liveIs, proposals)).toEqual(drawn);
    }
    expect(trackKeys(versions, null)).toEqual(versions.map((each) => each.sha.slice(0, 12)));
  });

  it("offer Diff only from two points", () => {
    expect(diffOffered(["v1"])).toBe(false);
    expect(diffOffered(["live"])).toBe(false);
    expect(diffOffered(["v1", "live"])).toBe(true);
  });
});

describe("going from One to Diff", () => {
  it("keeps the version as B and puts A on the one before it", () => {
    expect(oneToDiff(P, "v3")).toEqual({ a: "v2", b: "v3" });
    expect(oneToDiff(P, "live")).toEqual({ a: "v4", b: "live" });
  });

  it("on the oldest version moves B to the next one, A on the oldest", () => {
    expect(oneToDiff(P, "v1")).toEqual({ a: "v1", b: "v2" });
  });

  it("is not offered on one point", () => {
    expect(oneToDiff(["v1"], "v1")).toBeNull();
  });
});

describe("a range read from a link", () => {
  it("opens a reversed pair swapped, so Live is never A", () => {
    expect(normalise(P, "v3", "v1")).toEqual({ a: "v1", b: "v3" });
    expect(normalise(P, "live", "v2")).toEqual({ a: "v2", b: "live" });
  });

  it("is one version when both name the same point, or A is not on the track", () => {
    expect(normalise(P, "v2", "v2")).toEqual({ a: null, b: "v2" });
    expect(normalise(P, "gone", "v2")).toEqual({ a: null, b: "v2" });
    expect(normalise(P, "live", "live")).toEqual({ a: null, b: "live" });
  });

  it("is nothing when B is not on the track: the history's default applies", () => {
    expect(normalise(P, "v1", "gone")).toBeNull();
  });
});

describe("moving a handle", () => {
  const range: Range = { a: "v2", b: "v3" };

  it("past the other swaps the roles", () => {
    expect(moveTo(P, range, "a", 3, 1)).toEqual({ range: { a: "v3", b: "v4" }, side: "b" });
    expect(moveTo(P, range, "b", 0, -1)).toEqual({ range: { a: "v1", b: "v2" }, side: "a" });
  });

  it("dropped on the other's point goes one further in its direction", () => {
    expect(moveTo(P, range, "a", 2, 1)).toEqual({ range: { a: "v3", b: "v4" }, side: "b" });
    expect(moveTo(P, range, "b", 1, -1)).toEqual({ range: { a: "v1", b: "v2" }, side: "a" });
  });

  it("dropped on the other's point at the end of the track stays on its side", () => {
    expect(moveTo(P, { a: "v2", b: "live" }, "a", 4, 1)).toEqual({ range: { a: "v4", b: "live" }, side: "a" });
  });

  it("onto Live makes it B", () => {
    expect(moveTo(P, { a: "v1", b: "v2" }, "a", 4, 1)).toEqual({ range: { a: "v2", b: "live" }, side: "b" });
  });
});

describe("the keys", () => {
  const range: Range = { a: "v2", b: "v3" };

  it("← → step the focused handle, past the other one, and say where it went", () => {
    expect(stepHandle(P, range, "a", 1)).toEqual({ range: { a: "v3", b: "v4" }, side: "b" });
    expect(stepHandle(P, range, "a", -1)).toEqual({ range: { a: "v1", b: "v3" }, side: "a" });
    expect(stepHandle(P, { a: "v1", b: "v3" }, "a", -1)).toEqual({ range: { a: "v1", b: "v3" }, side: "a" });
  });

  it("Shift + ← → move both, keeping the distance, and stop at the ends", () => {
    expect(shiftBoth(P, range, 1)).toEqual({ a: "v3", b: "v4" });
    expect(shiftBoth(P, { a: "v4", b: "live" }, 1)).toEqual({ a: "v4", b: "live" });
    expect(shiftBoth(P, { a: "v1", b: "v3" }, -1)).toEqual({ a: "v1", b: "v3" });
  });

  it("the whole range dragged keeps its width and stops at the ends, so Live stays B", () => {
    expect(shiftBy(P, { a: "v1", b: "v2" }, 2)).toEqual({ a: "v3", b: "v4" });
    expect(shiftBy(P, { a: "v2", b: "v4" }, 5)).toEqual({ a: "v3", b: "live" });
    expect(shiftBy(P, { a: "v3", b: "live" }, -9)).toEqual({ a: "v1", b: "v3" });
    const same: Range = { a: "v2", b: "v3" };
    expect(shiftBy(P, same, 0)).toBe(same);
  });

  it("a step without the picker moves the version in One and the whole range in Diff, and stops at the ends", () => {
    expect(stepShown(P, null, "v2", 1)).toEqual({ a: null, b: "v3" });
    expect(stepShown(P, null, "v1", -1)).toBeNull();
    expect(stepShown(P, null, "live", 1)).toBeNull();
    expect(stepShown(P, "v2", "v3", -1)).toEqual({ a: "v1", b: "v2" });
    expect(stepShown(P, "v3", "live", 1)).toBeNull();
  });

  it("Home and End take the focused handle to the ends", () => {
    expect(homeEnd(P, range, "b", "end")).toEqual({ range: { a: "v2", b: "live" }, side: "b" });
    expect(homeEnd(P, range, "b", "home")).toEqual({ range: { a: "v1", b: "v2" }, side: "a" });
    expect(homeEnd(P, { a: "v1", b: "v3" }, "b", "home")).toEqual({ range: { a: "v1", b: "v2" }, side: "b" });
  });
});

describe("when the list changes", () => {
  it("an end that left moves toward the other", () => {
    expect(afterListChange(P, ["v1", "v3", "v4", "live"], { a: "v2", b: "v4" })).toEqual({ a: "v3", b: "v4" });
    expect(afterListChange(P, ["v1", "v2", "v4", "live"], { a: "v1", b: "v3" })).toEqual({ a: "v1", b: "v2" });
  });

  it("leaves one version when the two would meet", () => {
    expect(afterListChange(P, ["v1", "v3", "v4", "live"], { a: "v2", b: "v3" })).toEqual({ a: null, b: "v3" });
    expect(afterListChange(P, ["v1", "v2", "v4"], { a: "v4", b: "live" })).toEqual({ a: null, b: "v4" });
    expect(afterListChange(P, ["v1", "v2", "v4"], { a: "v2", b: "live" })).toEqual({ a: "v2", b: "v4" });
  });
});

describe("whatever is played on a track", () => {
  it("A stays before B, the two never meet, and Live is never A", () => {
    let seed = 7;
    const random = () => ((seed = (seed * 48271) % 2147483647) / 2147483647);
    for (const points of [["v1", "v2"], ["v1", "v2", "live"], Array.from({ length: 12 }, (_, at) => `v${at}`), [...Array.from({ length: 11 }, (_, at) => `v${at}`), "live"]]) {
      let range: Range = oneToDiff(points, points.at(-1)!)!;
      for (let move = 0; move < 2000; move += 1) {
        const handle = random() < 0.5 ? "a" : "b";
        const roll = random();
        const delta = random() < 0.5 ? -1 : 1;
        if (roll < 0.4) range = moveTo(points, range, handle, Math.floor(random() * points.length), delta).range;
        else if (roll < 0.7) range = stepHandle(points, range, handle, delta).range;
        else if (roll < 0.85) range = shiftBoth(points, range, delta);
        else range = homeEnd(points, range, handle, delta < 0 ? "home" : "end").range;
        expect(points.indexOf(range.a)).toBeLessThan(points.indexOf(range.b));
        expect(range.a).not.toBe("live");
      }
    }
  });
});

describe("open pull requests after Live", () => {
  const dated = (n: number, date: string): HistoryVersion => ({ ...version(n), date });
  const older = dated(8, "2026-01-01T00:00:00+00:00");
  const newer = dated(9, "2026-02-01T00:00:00+00:00");
  const versions = [version(1), version(2)];

  it("stand last, the oldest first, whatever order they came in", () => {
    expect(trackKeys(versions, "https://live", null, [newer, older])).toEqual([shortSha(versions[0]), shortSha(versions[1]), "live", shortSha(older), shortSha(newer)]);
    expect(proposalsByDate([newer, older]).map((each) => each.sha)).toEqual([older.sha, newer.sha]);
  });

  it("make Live an A, and a reversed pair is put right", () => {
    const keys = trackKeys(versions, "https://live", null, [older]);
    expect(normalise(keys, "live", shortSha(older))).toEqual({ a: "live", b: shortSha(older) });
    expect(normalise(keys, shortSha(older), "live")).toEqual({ a: "live", b: shortSha(older) });
    expect(oneToDiff(keys, shortSha(older))).toEqual({ a: "live", b: shortSha(older) });
  });

  it("with no Live follow the versions", () => {
    expect(trackKeys(versions, null, null, [older])).toEqual([shortSha(versions[0]), shortSha(versions[1]), shortSha(older)]);
  });
});
