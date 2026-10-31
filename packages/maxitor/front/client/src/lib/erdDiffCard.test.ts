// src/lib/erdDiffCard.test.ts
import { describe, expect, it } from "vitest";
import type { ErdEntity, ErdRelation } from "@/lib/buildDotSource";
import { diagramCounts } from "@/lib/erdDiff";
import { erdChanges } from "./erdDiffCard";

const ENTITIES: ErdEntity[] = [
  { id: "shop.Order", label: "Order", diff: "changed", fields: [{ name: "total", type: "int", diff: "added" }, { name: "note", type: "str", diff: "unchanged" }] },
  { id: "shop.Item", label: "Item", diff: "unchanged", fields: [{ name: "price", type: "int", diff: "removed" }] },
];
const RELATIONS: ErdRelation[] = [
  { source: "shop.Item", target: "shop.Order", source_field: "order", diff: "added" },
  { source: "shop.Item", target: "shop.Order", relationship_kind: "generalization", diff: "changed" },
];

describe("the ERD's changes", () => {
  it("list each table, then its rows, then the lines with no row, each with its cell", () => {
    expect(erdChanges(ENTITIES, RELATIONS).map(({ title, status, cell, group }) => ({ title, status, cell, group }))).toEqual([
      { title: "Order", status: "changed", cell: "a_hd0", group: "Order" },
      { title: "total", status: "added", cell: "a_fn0_0", group: "Order" },
      { title: "price", status: "removed", cell: "a_fn1_0", group: "Item" },
      { title: "Item → Order", status: "changed", cell: "re1", group: "Lines" },
    ]);
  });

  it("count as the button counts", () => {
    const { added, removed, changed } = diagramCounts(ENTITIES, RELATIONS);
    expect(erdChanges(ENTITIES, RELATIONS)).toHaveLength(added + removed + changed);
  });

  it("give a table and a row their cards, and a line none", () => {
    const changes = erdChanges(ENTITIES, RELATIONS);
    expect(changes[0].card?.elements).toEqual([{ kind: "node", id: "shop.Order" }]);
    expect(changes[1].card?.elements[0]).toEqual({ kind: "node", id: "shop.Order:total" });
    expect(changes[3].card).toBeNull();
  });
});
