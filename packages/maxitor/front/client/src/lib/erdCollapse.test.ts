import { describe, expect, it } from "vitest";
import type { ErdEntity, ErdRelation } from "@/lib/buildDotSource";
import { erdFolds, isCollapsed, rowsToHide } from "@/lib/erdCollapse";

const entity: ErdEntity = {
  id: "t",
  fields: [{ name: "id", primary_key: true }, { name: "owner", foreign_key: true }, { name: "plain" }, { name: "lined" }, { name: "changed", diff: "changed" }, { name: "same", diff: "unchanged" }],
};
const relations: ErdRelation[] = [{ source: "o", target: "t", target_field: "lined" }] as ErdRelation[];

describe("rowsToHide", () => {
  it("keeps keys, rows with a line and changed rows", () => {
    expect([...rowsToHide(entity, relations)]).toEqual([2, 5]);
  });

  it("hides every row of a table with no key and no line", () => {
    expect([...rowsToHide({ id: "x", fields: [{ name: "a" }, { name: "b" }] }, [])]).toEqual([0, 1]);
  });

  it("does not take another table's line of the same name", () => {
    expect(rowsToHide(entity, [{ source: "o", target: "other", target_field: "plain" }] as ErdRelation[]).has(2)).toBe(true);
  });
});

describe("isCollapsed", () => {
  it("is off by default", () => expect(isCollapsed("t", false, new Set())).toBe(false));
  it("collapses a table excepted from none", () => expect(isCollapsed("t", false, new Set(["t"]))).toBe(true));
  it("collapses a table arriving under all", () => expect(isCollapsed("new", true, new Set(["t"]))).toBe(true));
  it("leaves out a table excepted from all", () => expect(isCollapsed("t", true, new Set(["t"]))).toBe(false));
});

describe("erdFolds", () => {
  it("holds each table's fold", () => {
    expect(erdFolds([entity], relations, true, new Set()).get("t")).toEqual({ hidden: new Set([2, 5]), collapsed: true });
  });
});

describe("a selected row (spec 044)", () => {
  it("stays in a collapsed table", () => {
    const entity = { id: "t", fields: [{ name: "plain" }, { name: "kept" }] };
    expect(rowsToHide(entity, [])).toEqual(new Set([0, 1]));
    expect(rowsToHide(entity, [], "t:kept")).toEqual(new Set([0]));
  });
});
