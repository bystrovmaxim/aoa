// src/lib/erdDiffCard.test.ts
import { describe, expect, it } from "vitest";
import type { CompareResult } from "@/api/compare";
import type { ErdEntity, ErdRelation } from "@/lib/buildDotSource";
import { diagramCounts, lifecycleParts, markErd } from "@/lib/erdDiff";
import { erdChanges, LIFECYCLE_CHANGED } from "./erdDiffCard";

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

describe("a lifecycle's row", () => {
  const LC = "shop.Account:lifecycle:lifecycle";
  const COMPARED: CompareResult = {
    counts: { nodes: { added: 1, removed: 0, changed: 0 }, edges: { added: 2, removed: 0, changed: 0 } },
    nodes: { [`${LC}:frozen`]: "added" },
    edges: { [`${LC}|lifecycle_transition|${LC}:closed|provisioned`]: "added", [`${LC}|lifecycle_contains_state|${LC}:frozen`]: "added" },
  };

  it("lists the states and transitions that changed, which the ERD does not draw", () => {
    expect(lifecycleParts(LC, COMPARED).map(({ group, label, status }) => [group, label, status])).toEqual([
      ["States", "frozen", "added"],
      ["Transitions", "provisioned → closed", "added"],
    ]);
  });

  it("gives its card those parts and says the lifecycle changed", () => {
    const marked = markErd({ entities: [{ id: "shop.Account", label: "Account", fields: [{ name: "lifecycle", lifecycle_id: LC }] }], relations: [] }, COMPARED);
    const card = erdChanges(marked.entities!, []).find((change) => change.title === "lifecycle")?.card;
    expect(card?.note).toBe(LIFECYCLE_CHANGED);
    expect(card?.parts?.map((part) => part.label)).toEqual(["frozen", "provisioned → closed"]);
  });

  it("tells the same on the table, which changed only through its lifecycle", () => {
    const marked = markErd({ entities: [{ id: "shop.Account", label: "Account", fields: [{ name: "lifecycle", lifecycle_id: LC }] }], relations: [] }, COMPARED);
    const card = erdChanges(marked.entities!, []).find((change) => change.title === "Account")?.card;
    expect(card?.note).toBe(LIFECYCLE_CHANGED);
    expect(card?.parts).toHaveLength(2);
  });
});
