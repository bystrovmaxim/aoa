// src/lib/erdDiff.test.ts
import { describe, expect, it } from "vitest";
import type { CompareResult } from "@/api/compare";
import { buildDotSource, erdDiffMarks, erdEdgeId, erdPreviousEdgeId, type ErdEntity, type ErdRelation } from "./buildDotSource";
import { drawErdCards } from "./erdPostPass";
import { diagramCounts, erdHolds, erdOfSide, erdPortable, markErd, mergeErdSlices, nothingChanged, unmarked } from "./erdDiff";

const OFFER = "g.OfferEntity";
const CORE = "g.CoreEntity";
const DETAIL = "g.DetailEntity";
const STATE = "g.StateEntity";

function entity(id: string, fields: { name: string; type: string; foreign_key?: boolean }[]): ErdEntity {
  return { id, label: id.split(".")[1], color: "#3b82f6", fields };
}

const chosenToCore: ErdRelation = { source: OFFER, target: CORE, source_field: "chosen", source_cardinality: "zero_many", target_cardinality: "zero_one" };
const chosenToDetail: ErdRelation = { ...chosenToCore, target: DETAIL };

// A: Offer(id, erid: str, is_activated, chosen → Core), Core, Detail. B: is_activated gone, erid: str | None, a new
// field, chosen → Detail, a new table State.
const A = {
  entities: [entity(OFFER, [{ name: "id", type: "str" }, { name: "erid", type: "str" }, { name: "is_activated", type: "bool" }, { name: "chosen", type: "CoreEntity", foreign_key: true }]), entity(CORE, [{ name: "id", type: "str" }]), entity(DETAIL, [{ name: "id", type: "str" }])],
  relations: [chosenToCore],
};
const B = {
  entities: [
    entity(OFFER, [{ name: "id", type: "str" }, { name: "erid", type: "str | None" }, { name: "region", type: "str" }, { name: "chosen", type: "DetailEntity", foreign_key: true }]),
    entity(CORE, [{ name: "id", type: "str" }]),
    entity(DETAIL, [{ name: "id", type: "str" }]),
    entity(STATE, [{ name: "id", type: "str" }]),
  ],
  relations: [chosenToDetail],
};
const COMPARED: CompareResult = {
  counts: { nodes: { added: 3, removed: 1, changed: 2 }, edges: { added: 2, removed: 1, changed: 1 } },
  nodes: { [STATE]: "added", [`${STATE}:id`]: "added", [`${OFFER}:region`]: "added", [`${OFFER}:is_activated`]: "removed", [`${OFFER}:erid`]: "changed", [DETAIL]: "changed" },
  edges: { [`${OFFER}|entity_relation|chosen`]: "changed", [`${STATE}|entity_field|${STATE}:id`]: "added" },
};

const merged = markErd(mergeErdSlices(A, B), COMPARED);
const byId = (id: string) => merged.entities!.find((each) => each.id === id)!;
const row = (id: string, name: string) => byId(id).fields!.find((field) => field.name === name)!;

describe("the ERD of two versions", () => {
  it("draws the union: every table and row of either version", () => {
    expect(merged.entities!.map((each) => each.id)).toEqual([OFFER, CORE, DETAIL, STATE]);
    expect(byId(OFFER).fields!.map((field) => field.name)).toEqual(["id", "erid", "region", "chosen", "is_activated"]);
  });

  it("marks tables and rows by their graph elements' statuses, and everything else unchanged", () => {
    expect([byId(STATE).diff, byId(DETAIL).diff, byId(OFFER).diff, byId(CORE).diff]).toEqual(["added", "changed", "unchanged", "unchanged"]);
    expect([row(OFFER, "region").diff, row(OFFER, "is_activated").diff, row(OFFER, "erid").diff, row(OFFER, "id").diff]).toEqual(["added", "removed", "changed", "unchanged"]);
    expect(row(STATE, "id").diff).toBe("added");
  });

  it("keeps a changed type's old name, and a retargeted relation as one changed line with where it pointed", () => {
    expect(row(OFFER, "erid").previous_type).toBe("str");
    expect(row(OFFER, "chosen")).toMatchObject({ diff: "changed", previous_type: "CoreEntity" });
    expect(merged.relations).toMatchObject([{ ...chosenToDetail, previous_target: CORE, diff: "changed" }]);
  });

  it("counts each table, row and line once: a relation by its row, a row of a new table as added", () => {
    expect(diagramCounts(merged.entities!, merged.relations!)).toEqual({ added: 3, removed: 1, changed: 3 });
  });

  it("says no changes when nothing drawn changed, and draws it unmarked", () => {
    const calm = markErd(mergeErdSlices({ entities: [B.entities[1]] }, { entities: [B.entities[1]] }), COMPARED);
    const counts = diagramCounts(calm.entities!, []);
    expect(nothingChanged(counts)).toBe(true);
    const plain = unmarked({ entities: calm.entities!, relations: [] });
    expect(plain.entities[0]).not.toHaveProperty("diff");
    expect(buildDotSource(plain, "gv-dot-lr")).toBe(buildDotSource({ entities: [B.entities[1]], relations: [] }, "gv-dot-lr"));
  });
});

describe("the drawing of two versions", () => {
  const dot = buildDotSource({ entities: merged.entities!, relations: merged.relations! }, "gv-dot-lr");

  it("gives every mark its sign as well as its colour", () => {
    expect(dot).toContain("+ StateEntity");
    expect(dot).toContain("~ DetailEntity");
    expect(dot).toContain("+ region");
    expect(dot).toContain("<S>− is_activated</S>");
    expect(dot).toContain("~ erid");
  });

  it("writes a changed type struck through before the new one", () => {
    expect(dot).toContain("<S>str</S> → str | None");
  });

  it("draws a retargeted relation as one amber line to B's target and a thin dashed one to A's — no red, no green", () => {
    const toDetail = dot.split("\n").find((line) => line.includes(`id="${erdEdgeId(0)}"`))!;
    const toCore = dot.split("\n").find((line) => line.includes(`id="${erdPreviousEdgeId(0)}"`))!;
    expect(toDetail).toContain(`"${OFFER}" -> "${DETAIL}"`);
    expect(toDetail).toContain('color="#d97706"');
    expect(toDetail).not.toContain("style=dashed");
    expect(toCore).toContain(`"${OFFER}" -> "${CORE}"`);
    expect(toCore).toContain("style=dashed");
    expect(dot).not.toMatch(/-> "[^"]+" \[id="re\d+" color="#(16a34a|dc2626)"/);
  });

  it("is today's drawing, byte for byte, when nothing carries a mark", () => {
    expect(buildDotSource(A, "gv-dot-lr")).not.toContain("#16a34a");
    expect(buildDotSource(A, "gv-dot-lr")).toBe(buildDotSource(unmarked({ entities: markErd(A, COMPARED).entities!, relations: markErd(A, COMPARED).relations! }), "gv-dot-lr"));
  });

  it("fades the unchanged tables and dashes the removed ones' frames", () => {
    const gone = { ...entity("g.GoneEntity", []), diff: "removed" as const };
    const marks = erdDiffMarks([...merged.entities!, gone]);
    expect([...marks.faded]).toEqual([CORE]);
    expect([...marks.dashed]).toEqual(["g.GoneEntity"]);
    const svg =
      '<svg><g id="node1" class="node"><title>g.CoreEntity</title><path fill="white" stroke="none" d="M0,0 L10,0 L10,10 L0,10 Z"/><path fill="none" stroke="#3b82f6" d="M0,0 L10,0 L10,10 L0,10 Z"/></g>' +
      '<g id="node2" class="node"><title>g.GoneEntity</title><path fill="white" stroke="none" d="M0,0 L10,0 L10,10 L0,10 Z"/><path fill="none" stroke="#dc2626" d="M0,0 L10,0 L10,10 L0,10 Z"/></g></svg>';
    const drawn = drawErdCards(svg, 9, 1.4, marks);
    expect(drawn).toContain('<g id="node1" class="node" opacity="0.32">');
    expect(drawn).toMatch(/<rect fill="none" stroke="#dc2626" stroke-width="1.4" stroke-dasharray="5 3"/);
    expect(drawErdCards(svg, 9, 1.4)).not.toContain("opacity");
  });
});

describe("the part of a drawing one version has (spec 044)", () => {
  const field = (name: string, type = "str") => ({ name, type });
  const older = {
    entities: [
      { id: "b.Second", fields: [field("z"), field("gone"), field("kept", "int")] },
      { id: "b.Removed", fields: [field("x")] },
      { id: "b.First", fields: [field("y")] },
    ],
    relations: [
      { source: "b.First", target: "b.Second", source_field: "to", relationship_kind: "AssociationOne" },
      { source: "b.Removed", target: "b.Second", source_field: "dead", relationship_kind: "AssociationOne" },
    ],
  };
  const newer = {
    entities: [
      { id: "b.First", fields: [field("y")] },
      { id: "b.Second", fields: [field("kept", "str"), field("z"), field("fresh")] },
      { id: "b.Added", fields: [field("n")] },
    ],
    relations: [{ source: "b.First", target: "b.Added", source_field: "to", relationship_kind: "AssociationOne" }],
  };
  const compared = {
    counts: { nodes: { added: 0, removed: 0, changed: 0 }, edges: { added: 0, removed: 0, changed: 0 } },
    nodes: { "b.Removed": "removed", "b.Added": "added", "b.Second:gone": "removed", "b.Second:fresh": "added", "b.Second:kept": "changed", "b.Removed:x": "removed", "b.Added:n": "added" },
    edges: { "b.First|entity_relation|to": "changed", "b.Removed|entity_relation|dead": "removed" },
  } as unknown as CompareResult;
  const merged = markErd(mergeErdSlices(older, newer), compared) as { entities: ErdEntity[]; relations: ErdRelation[] };
  /** What the layout reads of a drawing. */
  const shape = (data: { entities: ErdEntity[]; relations?: ErdRelation[] }) => ({
    tables: data.entities.map((entity) => [entity.id, (entity.fields ?? []).map((each) => `${each.name}:${each.type}`)]),
    lines: (data.relations ?? []).map((relation) => `${relation.source}>${relation.target}`),
  });

  it("stands A as A had it: its tables, rows, order, types and targets", () => {
    expect(shape(erdOfSide(merged, "a"))).toEqual(shape(older));
  });

  it("stands B as B has it", () => {
    expect(shape(erdOfSide(merged, "b"))).toEqual(shape(newer));
  });

  it("marks a table on both halves when a row changed on either", () => {
    const newRow = markErd(mergeErdSlices({ entities: [{ id: "b.T", fields: [field("x")] }] }, { entities: [{ id: "b.T", fields: [field("x"), field("new")] }] }), {
      ...compared,
      nodes: { "b.T:new": "added" },
      edges: {},
    } as unknown as CompareResult) as { entities: ErdEntity[]; relations: ErdRelation[] };
    const [a, b] = [erdOfSide(newRow, "a").entities[0], erdOfSide(newRow, "b").entities[0]];
    expect(a.diff).toBe("changed");
    expect(b.diff).toBe("changed");
    expect(a.fields?.map((row) => row.name)).toEqual(["x"]);
  });

  it("keeps the marks each version can show", () => {
    const a = erdOfSide(merged, "a");
    expect(a.entities.find((entity) => entity.id === "b.Removed")?.diff).toBe("removed");
    expect(a.entities.flatMap((entity) => entity.fields ?? []).find((each) => each.name === "kept")?.diff).toBe("changed");
    expect(a.relations[0].diff).toBe("changed");
    const b = erdOfSide(merged, "b");
    expect(b.entities.find((entity) => entity.id === "b.Added")?.diff).toBe("added");
  });
});

describe("a table, a row and a line across the two halves (spec 044)", () => {
  const entities = [{ id: "b.One", fields: [{ name: "x" }] }, { id: "b.Two", fields: [{ name: "y" }, { name: "z" }] }] as ErdEntity[];
  const relations = [{ source: "b.One", target: "b.Two", source_field: "x" }] as ErdRelation[];
  const other = [entities[1], entities[0]];

  it("names a row by what it is, so the other half finds it at its own place", () => {
    const shared = erdPortable(() => ({ entities, relations })).toIdentity({ kind: "row", id: "fn1_1" });
    expect(shared).toEqual({ kind: "row", id: "b.Two:z" });
    expect(erdPortable(() => ({ entities: other })).fromIdentity(shared)).toEqual({ kind: "row", id: "fn0_1" });
  });

  it("names a line by what it is, and finds no line the drawing lacks", () => {
    const shared = erdPortable(() => ({ entities, relations })).toIdentity({ kind: "edge", id: "re0" });
    expect(shared).toEqual({ kind: "edge", id: "b.One|x" });
    expect(erdPortable(() => ({ entities, relations: [] })).fromIdentity(shared)).toBeNull();
  });

  it("knows what a version holds", () => {
    const data = { entities, relations };
    expect(erdHolds(data, { kind: "table", id: "b.Two" })).toBe(true);
    expect(erdHolds(data, { kind: "row", id: "b.Two:z" })).toBe(true);
    expect(erdHolds(data, { kind: "row", id: "b.Two:gone" })).toBe(false);
    expect(erdHolds(data, { kind: "table", id: "b.Three" })).toBe(false);
  });
});
