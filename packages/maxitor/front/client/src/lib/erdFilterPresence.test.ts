// src/lib/erdFilterPresence.test.ts
import { describe, expect, it } from "vitest";
import type { ErdDiff, ErdEntity } from "@/lib/buildDotSource";
import { changesOnDiagram, onScreen } from "./erdFilterPresence";

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
  const drawn = [table("w", "inventory", "core", "added"), table("n", "catalog", "detail", "unchanged")];

  it("is every domain, kind and change of the tables drawn — a 1-hop neighbour counts like any table", () => {
    const shown = onScreen(drawn, new Set(), domainOf);
    expect([...shown.domains].sort()).toEqual(["catalog", "inventory"]);
    expect([...shown.kinds].sort()).toEqual(["core", "detail"]);
    expect([...shown.changes].sort()).toEqual(["added", "unchanged"]);
  });

  it("leaves out the tables of a kind of change switched off, and with them their domain and kind", () => {
    const shown = onScreen(drawn, new Set(["unchanged"]), domainOf);
    expect([...shown.ids]).toEqual(["w"]);
    expect([...shown.domains]).toEqual(["inventory"]);
    expect([...shown.kinds]).toEqual(["core"]);
  });
});
