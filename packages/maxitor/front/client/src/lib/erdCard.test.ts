import { describe, expect, it } from "vitest";
import type { ErdEntity, ErdRelation } from "@/lib/buildDotSource";
import type { CompareResult } from "@/api/compare";
import { erdSubject, fromAfar, litBy } from "@/lib/erdCard";
import { markErd } from "@/lib/erdDiff";

const entities: ErdEntity[] = [
  { id: "a.Lot", label: "Lot", entity_kind_label: "Core", fields: [{ name: "id", type: "str", primary_key: true, description: "Lot id" }] },
  { id: "a.Offer", label: "Offer", diff: "changed", fields: [{ name: "price", type: "int", diff: "unchanged" }, { name: "chosen", type: "str", diff: "changed", annotation: "Optional[str]" }, { name: "status", type: "S", lifecycle_id: "a.Offer:lifecycle:status" }] },
];
const root = document.createElement("div");

describe("erdSubject", () => {
  it("gives an unchanged row its name and type, and no change", () => {
    const subject = erdSubject({ kind: "row", id: "fn1_0" }, entities, root);
    expect(subject).toMatchObject({ title: "price", detail: "int", nodeId: null, change: null, lifecycleIds: [], copy: "price" });
  });

  it("gives a changed row every element it stands for", () => {
    const subject = erdSubject({ kind: "row", id: "ft1_1" }, entities, root);
    expect(subject?.change?.elements.map((element) => element.id)).toEqual(["a.Offer:chosen", "a.Offer|entity_field|a.Offer:chosen", "a.Offer|entity_relation|chosen"]);
    expect(subject?.detail).toBe("Optional[str]");
  });

  it("gives a row its description", () => {
    const table: ErdEntity = { id: "t", fields: [{ name: "owner", foreign_key: true, description: "Who owns it" }] };
    expect(erdSubject({ kind: "row", id: "fn0_0" }, [table], root)?.description).toBe("Who owns it");
    expect(erdSubject({ kind: "table", id: "t" }, [table], root)?.fields?.[0]?.description).toBe("Who owns it");
  });

  it("names a row's lifecycle", () => {
    expect(erdSubject({ kind: "row", id: "fn1_2" }, entities, root)?.lifecycleIds).toEqual(["a.Offer:lifecycle:status"]);
  });

  it("lists a table's fields, keys marked", () => {
    expect(erdSubject({ kind: "table", id: "a.Lot" }, entities, root)).toMatchObject({ detail: "", nodeId: "a.Lot", change: null, fields: [{ name: "id", type: "str", key: "PK", description: "Lot id" }] });
  });

  it("shows a table's lifecycles", () => {
    expect(erdSubject({ kind: "table", id: "a.Offer" }, entities, root)?.lifecycleIds).toEqual(["a.Offer:lifecycle:status"]);
    expect(erdSubject({ kind: "table", id: "a.Lot" }, entities, root)?.lifecycleIds).toEqual([]);
  });

  it("tells a changed table", () => {
    expect(erdSubject({ kind: "table", id: "a.Offer" }, entities, root)?.change).toEqual({ title: "Offer", status: "changed", elements: [{ kind: "node", id: "a.Offer" }] });
  });

  it("tells a line in the model's words, with no paths", () => {
    const relations = [{ source: "a.Lot", target: "a.Offer", source_field: "offer", target_field: "lots", relationship_kind: "association", source_cardinality: "zero_many", target_cardinality: "one", description: "The offer it came from", diff: "added" }] as ErdRelation[];
    expect(erdSubject({ kind: "edge", id: "re0" }, entities, root, relations)).toMatchObject({ title: "Lot.offer → Offer.lots", detail: "Association · 0..* → 1", description: "The offer it came from", change: { status: "added" } });
  });

  it("has nothing for a line it does not know or an unknown table", () => {
    expect(erdSubject({ kind: "edge", id: "re1" }, entities, root)).toBeNull();
    expect(erdSubject({ kind: "table", id: "a.None" }, entities, root)).toBeNull();
  });
});

describe("a row from afar (spec 043)", () => {
  const cell = (height: number) => ({ getBoundingClientRect: () => ({ height }) }) as Element;
  const row = { kind: "row", id: "fn1_0" } as const;

  it("stands for its table when it cannot be read", () => {
    expect(fromAfar(row, cell(9), entities, false)).toEqual({ kind: "table", id: "a.Offer" });
  });

  it("stays a row when it can", () => expect(fromAfar(row, cell(10), entities, false)).toBe(row));

  it("asks more of a finger", () => {
    expect(fromAfar(row, cell(15), entities, true)).toEqual({ kind: "table", id: "a.Offer" });
    expect(fromAfar(row, cell(20), entities, true)).toBe(row);
  });
});

describe("a table's card in Diff", () => {
  it("marks a table whose fields changed, though it did not", () => {
    const table: ErdEntity = { id: "t", diff: "unchanged", fields: [{ name: "same", diff: "unchanged" }, { name: "typed", diff: "changed" }] };
    expect(erdSubject({ kind: "table", id: "t" }, [table], root)?.change).toMatchObject({ status: "changed", note: "Its fields changed." });
  });

  it("leaves a table of no change unmarked", () => {
    expect(erdSubject({ kind: "table", id: "t" }, [{ id: "t", diff: "unchanged", fields: [{ name: "same", diff: "unchanged" }] }], root)?.change).toBeNull();
  });

  it("says a table moved to another domain", () => {
    const table: ErdEntity = { id: "t", diff: "changed", movedDomain: true, fields: [] };
    expect(erdSubject({ kind: "table", id: "t" }, [table], root)?.change?.note).toBe("Moved to another domain.");
  });

  it("puts what changed first, with its mark and earlier type", () => {
    const table: ErdEntity = { id: "t", fields: [{ name: "same", diff: "unchanged" }, { name: "new", diff: "added" }, { name: "typed", type: "int", previous_type: "str", diff: "changed" }] };
    const fields = erdSubject({ kind: "table", id: "t" }, [table], root)?.fields;
    expect(fields?.map((field) => [field.name, field.status])).toEqual([["new", "added"], ["typed", "changed"], ["same", undefined]]);
    expect(fields?.[1]?.previousType).toBe("str");
  });
});

describe("a table that changed domain (spec 043)", () => {
  it("is marked changed though its own properties are not", () => {
    const compared: CompareResult = { counts: { nodes: { added: 0, removed: 0, changed: 0 }, edges: { added: 1, removed: 1, changed: 0 } }, nodes: {}, edges: { "t|domain|a": "removed", "t|domain|b": "added" } };
    const [moved, still] = markErd({ entities: [{ id: "t" }, { id: "u" }] }, compared).entities!;
    expect([moved?.diff, moved?.movedDomain]).toEqual(["changed", true]);
    expect([still?.diff, still?.movedDomain]).toEqual(["unchanged", false]);
  });
});

describe("litBy", () => {
  const tables: ErdEntity[] = [{ id: "a", fields: [{ name: "owner" }, { name: "plain" }] }, { id: "b" }, { id: "c" }];
  const lines = [{ source: "a", target: "b", source_field: "owner" }, { source: "c", target: "a", source_field: "ref", target_field: "plain" }, { source: "a", target: "a", source_field: "peer" }] as ErdRelation[];

  it("of a table: every table it joins, never itself, and all its lines", () => {
    expect(litBy({ kind: "table", id: "a" }, tables, lines)).toEqual({ tables: ["b", "c"], lines: [0, 1, 2] });
  });

  it("of a row: only what its own lines reach", () => {
    expect(litBy({ kind: "row", id: "fn0_0" }, tables, lines)).toEqual({ tables: ["b"], lines: [0] });
    expect(litBy({ kind: "row", id: "fn0_1" }, tables, lines)).toEqual({ tables: ["c"], lines: [1] });
  });

  it("of a line: its two ends and itself", () => {
    expect(litBy({ kind: "edge", id: "re0" }, tables, lines)).toEqual({ tables: ["a", "b"], lines: [0] });
  });
});
