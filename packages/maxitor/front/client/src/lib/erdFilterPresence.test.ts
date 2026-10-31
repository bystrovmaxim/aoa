// src/lib/erdFilterPresence.test.ts
import { describe, expect, it } from "vitest";
import type { ErdDiff, ErdEntity, ErdGraphPayload } from "@/lib/buildDotSource";
import { changesOnDiagram, filterGraphByChanges, onScreen, withOneHop } from "./erdFilterPresence";

const table = (id: string, domain: string, kind: string, diff?: ErdDiff, rowDiff?: ErdDiff): ErdEntity =>
  ({ id, label: id, domain_qualname: domain, entity_kind: kind, diff, fields: [{ name: "id", type: "str", diff: rowDiff }] }) as unknown as ErdEntity;
const domainOf = (entity: ErdEntity) => entity.domain_qualname ?? null;

describe("the Changes rows of a diagram (its base)", () => {
  it("are the kinds of change the diagram has, in the filter's order", () => {
    expect(changesOnDiagram([table("a", "d", "core", "unchanged"), table("b", "d", "core", "added"), table("c", "d", "core", "unchanged", "changed")])).toEqual(["added", "changed", "unchanged"]);
  });

  it("are none when nothing on the diagram changed", () => {
    expect(changesOnDiagram([table("a", "d", "core", "unchanged"), table("b", "d", "core", "unchanged")])).toEqual([]);
  });

  it("are none when one version is drawn", () => {
    expect(changesOnDiagram([table("a", "d", "core")])).toEqual([]);
  });
});

describe("what the screen shows of each filter", () => {
  it("is every domain, kind and change of the tables shown — a 1-hop neighbour counts like any table, for its own domain", () => {
    const shown = onScreen([table("w", "inventory", "core", "added"), table("n", "catalog", "detail", "unchanged")], domainOf);
    expect([...shown.domains].sort()).toEqual(["catalog", "inventory"]);
    expect([...shown.kinds].sort()).toEqual(["core", "detail"]);
    expect([...shown.changes].sort()).toEqual(["added", "unchanged"]);
  });
});

describe("a kind of change switched off", () => {
  const graph = {
    entities: [table("New", "d", "core", "added"), table("Same", "d", "core", "unchanged"), table("Far", "d", "core", "unchanged")],
    relations: [{ source: "New", target: "Same" }, { source: "Same", target: "Far" }],
  } as unknown as ErdGraphPayload;

  it("hides its tables and their lines, as a domain or a kind switched off does", () => {
    const kept = filterGraphByChanges(graph, new Set(["unchanged"]));
    expect(kept.entities.map((entity) => entity.id)).toEqual(["New"]);
    expect(kept.relations).toEqual([]);
  });

  it("is brought back by 1-hop one line away from the tables left — and no further", () => {
    const shown = withOneHop(filterGraphByChanges(graph, new Set(["unchanged"])), graph);
    expect(shown.entities.map((entity) => entity.id)).toEqual(["New", "Same"]);
    expect(shown.relations).toEqual([{ source: "New", target: "Same" }]);
  });
});
