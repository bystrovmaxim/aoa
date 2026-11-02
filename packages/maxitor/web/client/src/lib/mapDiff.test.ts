// src/lib/mapDiff.test.ts
import { describe, expect, it } from "vitest";
import type { MapChange } from "@/api/map";
import { changeLines, type ChangeEntry } from "./changeStepping";
import { changesByArea, countChanges, firstChangeOf, nextChange } from "./mapDiff";

const CHANGES = [
  { area: "a", status: "added" },
  { area: "a", status: "changed" },
  { area: "b", status: "changed" },
] as MapChange[];

describe("the counts of a pair", () => {
  it("count every change by status, nodes and links alike", () => {
    expect(countChanges(CHANGES)).toEqual({ added: 1, removed: 0, changed: 2 });
  });

  it("count a link as a change like any other", () => {
    expect(countChanges([{ status: "changed", span: 40 }] as MapChange[])).toEqual({ added: 0, removed: 0, changed: 1 });
  });

  it("count an area's changes, and name only the areas that hold one", () => {
    const areas = changesByArea(CHANGES);
    expect(areas.get("a")).toEqual({ added: 1, removed: 0, changed: 1 });
    expect(areas.has("c")).toBe(false);
  });

  it("read nothing of an empty list", () => {
    expect(countChanges([])).toEqual({ added: 0, removed: 0, changed: 0 });
  });
});

describe("stepping through changes", () => {
  it("starts from the first or the last", () => {
    expect(nextChange(null, 1, 3)).toBe(0);
    expect(nextChange(null, -1, 3)).toBe(2);
  });

  it("wraps around at both ends", () => {
    expect(nextChange(2, 1, 3)).toBe(0);
    expect(nextChange(0, -1, 3)).toBe(2);
  });

  it("finds an area's first change", () => {
    const changes = [{ area: "a" }, { area: "b" }, { area: "b" }] as MapChange[];
    expect(firstChangeOf(changes, "b")).toBe(1);
    expect(firstChangeOf(changes, "c")).toBe(-1);
  });
});

describe("the list of changes", () => {

  it("names each group above its changes", () => {
    const entries = [{ key: "a", group: "Sales" }, { key: "b", group: "Sales" }, { key: "c", group: "Store" }] as ChangeEntry[];
    expect(changeLines(entries).map((line) => ("group" in line ? line.group : line.position))).toEqual(["Sales", 0, 1, "Store", 2]);
  });
});
