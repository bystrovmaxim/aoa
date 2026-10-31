// src/lib/mapVisibility.test.ts
import { describe, expect, it } from "vitest";
import type { MapArea, MapBundle, MapChange, MapOverview } from "@/api/map";
import { areaLeft, bundleLeft, cellsLeft, changesLeft, mapFacts, nodeLeft, presence, type MapFilters } from "./mapVisibility";

const SALES: MapArea = {
  id: "sales",
  name: "Sales",
  colour: "#111111",
  x: 0,
  y: 0,
  radius: 100,
  counts: { Entity: 2, EntityField: 3, Action: 1 },
  sketch: {
    cell: 60,
    cells: [
      [0, 0, 1, 2, 0, 0],
      [0, 1, 2, 3, 1, 0],
      [1, 1, 0, 1, 0, 1],
    ],
  },
};
const OUTSIDE: MapArea = { ...SALES, id: "(outside)", sketch: { cell: 60, cells: [[0, 0, 1, 1, 0, 0]] } };
const OVERVIEW: MapOverview = { state: "ready", types: ["Action", "Entity", "EntityField"], type_colours: {}, chains: [[], ["Entity"]], areas: [SALES, OUTSIDE], bundles: [], shared: [{ id: "both", domains: ["sales", "store"] }] };
const FACTS = mapFacts(OVERVIEW);

function off(filters: Partial<Record<keyof MapFilters, string[]>>): MapFilters {
  return { types: new Set(filters.types), domains: new Set(filters.domains), changes: new Set(filters.changes) };
}

function total(cells: { 3: number }[]): number {
  return cells.reduce((sum, cell) => sum + cell[3], 0);
}

describe("what a type switched off leaves", () => {
  it("takes its own nodes", () => {
    expect(total(cellsLeft(SALES, off({ types: ["Action"] }), FACTS))).toBe(5);
  });

  it("takes what those nodes contain", () => {
    expect(total(cellsLeft(SALES, off({ types: ["Entity"] }), FACTS))).toBe(1);
  });

  it("takes all that stands below a domain when the type Domain goes, and leaves what is outside domains", () => {
    const facts = mapFacts({ ...OVERVIEW, chains: [["Domain"], ["Domain", "Entity"]] });
    expect(cellsLeft(SALES, off({ types: ["Domain"] }), facts)).toEqual([]);
    expect(nodeLeft(off({ types: ["Domain"] }), facts, "free", "(outside)", "Role", -1, "unchanged")).toBe(true);
  });

  it("does not reach up: a field switched off leaves its entity", () => {
    expect(total(cellsLeft(SALES, off({ types: ["EntityField"] }), FACTS))).toBe(3);
  });
});

describe("what a domain switched off leaves", () => {
  it("takes the area", () => {
    expect(cellsLeft(SALES, off({ domains: ["sales"] }), FACTS)).toEqual([]);
  });

  it("leaves a node of another domain until all of them are off", () => {
    expect(nodeLeft(off({ domains: ["sales"] }), FACTS, "both", "sales", "Entity", 0, "unchanged")).toBe(true);
    expect(nodeLeft(off({ domains: ["sales", "store"] }), FACTS, "both", "sales", "Entity", 0, "unchanged")).toBe(false);
  });

  it("never takes a node in no domain", () => {
    expect(nodeLeft(off({ domains: ["sales", "(outside)"] }), FACTS, "free", "(outside)", "Entity", 0, "unchanged")).toBe(true);
  });
});

describe("what a kind of change switched off leaves", () => {
  it("takes the nodes of that glance", () => {
    expect(total(cellsLeft(SALES, off({ changes: ["unchanged"] }), FACTS))).toBe(1);
    expect(nodeLeft(off({ changes: ["added"] }), FACTS, "a", "sales", "Action", 0, "added")).toBe(false);
  });
});

describe("what is left of an area", () => {
  it("is the whole area, at its own place, when nothing is cut", () => {
    expect(areaLeft(SALES, off({}), FACTS)).toEqual({ left: 6, total: 6, x: 0, y: 0, radius: 100 });
  });

  it("stands with what is left, and reads how much of how much", () => {
    const left = areaLeft(SALES, off({ types: ["Entity"] }), FACTS);
    expect(left).toMatchObject({ left: 1, total: 6, x: 90, y: 90 });
    expect(left.radius).toBeLessThan(SALES.radius * 3);
  });

  it("leaves nothing of a domain switched off", () => {
    expect(areaLeft(SALES, off({ domains: ["sales"] }), FACTS).left).toBe(0);
  });

  it("says nothing is cut of an area with no sketch that stays on", () => {
    const failed = { ...SALES, sketch: undefined };
    expect(areaLeft(failed, off({}), FACTS)).toMatchObject({ left: 1, total: 1 });
    expect(areaLeft(failed, off({ domains: ["sales"] }), FACTS).left).toBe(0);
  });
});

describe("a bundle", () => {
  const BUNDLE: MapBundle = ["sales", "store", 5, { "Entity|Action": 3, "EntityField>Entity|Action": 2 }, { added: 1, changed: 1 }];

  it("counts what is left of it", () => {
    expect(bundleLeft(BUNDLE, off({}))).toBe(5);
    expect(bundleLeft(BUNDLE, off({ types: ["Entity"] }))).toBe(0);
    expect(bundleLeft(BUNDLE, off({ types: ["EntityField"] }))).toBe(3);
  });

  it("goes with either domain", () => {
    expect(bundleLeft(BUNDLE, off({ domains: ["store"] }))).toBe(0);
  });

  it("holds only its changes when the unchanged are off", () => {
    expect(bundleLeft(BUNDLE, off({ changes: ["unchanged"] }))).toBe(2);
    expect(bundleLeft(BUNDLE, off({ changes: ["unchanged", "added"] }))).toBe(1);
    expect(bundleLeft(BUNDLE, off({ changes: ["added"] }))).toBe(4);
  });
});

describe("the changes left", () => {
  const FIELD = { id: "f", status: "added", ends: [["f", "sales", "EntityField", 1, "added"]] } as MapChange;
  const LINK = { id: "l", status: "changed", ends: [["a", "sales", "Entity", 0, "changed"], ["b", "(outside)", "Action", 0, "changed"]] } as MapChange;

  it("goes by the change's own status", () => {
    expect(changesLeft([FIELD, LINK], off({ changes: ["added"] }), FACTS)).toEqual([LINK]);
  });

  it("takes a change with what contains it", () => {
    expect(changesLeft([FIELD], off({ types: ["Entity"] }), FACTS)).toEqual([]);
  });

  it("takes a link when either end goes", () => {
    expect(changesLeft([LINK], off({ types: ["Action"] }), FACTS)).toEqual([]);
  });
});

describe("how much of each row is left", () => {
  it("measures a row with its own switch left out, so the two axes stay apart", () => {
    const rows = presence(OVERVIEW, off({ types: ["Entity"] }), FACTS);
    expect(rows.types.get("Entity")?.left).toBe(3);
    expect(rows.types.get("EntityField")).toMatchObject({ left: 0, total: 3, hiddenBy: [{ section: "types", key: "Entity" }] });
  });

  it("says what keeps a domain off the screen", () => {
    const rows = presence(OVERVIEW, off({ types: ["Entity", "Action"] }), FACTS);
    const sales = rows.domains.get("sales");
    expect(sales?.left).toBe(0);
    expect(sales?.hiddenBy.map((reason) => reason.key).sort()).toEqual(["Action", "Entity"]);
  });

  it("keeps the count of a row whose domain is off", () => {
    expect(presence(OVERVIEW, off({ domains: ["sales"] }), FACTS).types.get("Action")).toMatchObject({ left: 0, total: 1 });
  });
});
