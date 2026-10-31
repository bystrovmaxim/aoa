// src/lib/mapFilterRows.test.ts
import { describe, expect, it, vi } from "vitest";
import type { MapOverview } from "@/api/map";
import { mapFilterRows } from "./mapFilterRows";
import { mapFacts, presence, type MapFilters } from "./mapVisibility";

const OVERVIEW: MapOverview = {
  state: "ready",
  types: ["Entity", "EntityField"],
  type_colours: { Entity: "#059669" },
  chains: [[], ["Entity"]],
  areas: [
    { id: "sales", name: "Sales", colour: "#111111", x: 0, y: 0, radius: 9, counts: {}, sketch: { cell: 60, cells: [[0, 0, 0, 2, 0, 3], [0, 1, 1, 3, 1, 0]] } },
    { id: "(outside)", name: "(outside)", colour: "#222222", x: 0, y: 0, radius: 9, counts: {} },
  ],
  bundles: [],
  shared: [],
};

function rows(types: string[], paint: "domains" | "kinds" | "changes" = "domains", reveal = vi.fn()) {
  const filters: MapFilters = { types: new Set(types), domains: new Set(), changes: new Set() };
  return mapFilterRows(OVERVIEW, filters, presence(OVERVIEW, filters, mapFacts(OVERVIEW)), paint, true, reveal);
}

describe("the map's filter rows", () => {
  it("list domains without what is outside them", () => {
    expect(rows([]).domainRows.map((row) => row.key)).toEqual(["sales"]);
  });

  it("dim a row taken by something else, keep it on, and say what took it", () => {
    const field = rows(["Entity"]).typeRows.find((row) => row.key === "EntityField");
    expect(field).toMatchObject({ on: true, absent: true });
    expect(field?.hidden?.by.map((reason) => reason.label)).toEqual(["Entity"]);
  });

  it("leave a row switched off without a reason: the two look different", () => {
    const entity = rows(["Entity"]).typeRows.find((row) => row.key === "Entity");
    expect(entity).toMatchObject({ on: false, absent: false, hidden: undefined });
  });

  it("offer to switch on what took a row", () => {
    const reveal = vi.fn();
    rows(["Entity"], "domains", reveal).typeRows.find((row) => row.key === "EntityField")?.hidden?.onReveal();
    expect(reveal).toHaveBeenCalledWith([{ section: "types", key: "Entity" }]);
  });

  it("list only the kinds of change the pair has", () => {
    expect(rows([]).changeRows.map((row) => row.key)).toEqual(["changed", "unchanged"]);
  });

  it("paint disks only in the section that paints", () => {
    const grey = decodeURIComponent(rows([], "domains").typeRows[0].iconSrc);
    const painted = decodeURIComponent(rows([], "kinds").typeRows[0].iconSrc);
    expect(grey).toContain("#cbd5e1");
    expect(painted).toContain("#059669");
  });
});
