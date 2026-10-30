// src/lib/erdPaint.test.ts
import { afterEach, describe, expect, it } from "vitest";
import { buildDotSource, ERD_DIFF_COLOUR, erdDiffMarks, setErdPaint, type ErdDiff, type ErdEntity } from "@/lib/buildDotSource";
import { setPaintSections, setPaintSource, useErdPaint } from "@/lib/erdPaint";
import { renderHook, act } from "@testing-library/react";

const DOMAIN = "#e11d48";
const KIND = "#3b82f6";
const QUIET_HEAD = "#e2e8f0";
const QUIET_FRAME = "#cbd5e1";

const table = (id: string, diff?: ErdDiff, rowDiff?: ErdDiff): ErdEntity =>
  ({ id, label: id, color: DOMAIN, entity_kind: "core", diff, fields: [{ name: "id", type: "str", primary_key: true, diff: rowDiff }] }) as unknown as ErdEntity;

/** A table's header fill and frame colour as the DOT draws them. */
function look(dot: string, id: string): { head: string; frame: string } {
  const node = dot.split("\n").find((line) => line.startsWith(`  "${id}" [label=`)) ?? "";
  return { frame: /STYLE="ROUNDED" COLOR="([^"]+)"/.exec(node)?.[1] ?? "", head: /<TD COLSPAN="3" BGCOLOR="([^"]+)"/.exec(node)?.[1] ?? "" };
}

const draw = (entities: ErdEntity[]) => buildDotSource({ entities, relations: [] }, "gv-dot-lr");

afterEach(() => setErdPaint("change", {}));

describe("Diff painted by changes (spec 038)", () => {
  const dot = () => (setErdPaint("change", {}), draw([table("Added", "added"), table("Removed", "removed"), table("Inside", "unchanged", "changed"), table("Own", "changed"), table("Same", "unchanged")]));

  it("paints a table added or removed whole green or red, header and frame", () => {
    expect(look(dot(), "Added")).toEqual({ head: ERD_DIFF_COLOUR.added, frame: ERD_DIFF_COLOUR.added });
    expect(look(dot(), "Removed")).toEqual({ head: ERD_DIFF_COLOUR.removed, frame: ERD_DIFF_COLOUR.removed });
  });

  it("paints a table changed inside — a row, or its own properties — amber, header and frame", () => {
    expect(look(dot(), "Inside")).toEqual({ head: ERD_DIFF_COLOUR.changed, frame: ERD_DIFF_COLOUR.changed });
    expect(look(dot(), "Own")).toEqual({ head: ERD_DIFF_COLOUR.changed, frame: ERD_DIFF_COLOUR.changed });
  });

  it("signs the name of every changed table — added +, removed −, changed ~ whether a row or its own properties changed", () => {
    const names = [...dot().matchAll(/<B>([^<]*)<\/B><\/FONT><\/TD><\/TR><\/TABLE>/g)].map((m) => m[1]);
    expect(names).toEqual(["+ Added", "− Removed", "~ Inside", "~ Own", "Same"]);
  });

  it("keeps a table that did not change quiet: a grey header and a grey frame", () => {
    expect(look(dot(), "Same")).toEqual({ head: QUIET_HEAD, frame: QUIET_FRAME });
  });

  it("draws the key words grey, not in their colours", () => {
    expect(dot()).toContain('COLOR="#94a3b8"><B>PK</B>');
  });
});

describe("Diff painted by domains or kinds", () => {
  it("gives every header the domain's colour, a changed table's too, and tells the change by its frame", () => {
    setErdPaint("domain", {});
    const dot = draw([table("Added", "added"), table("Same", "unchanged")]);
    expect(look(dot, "Added")).toEqual({ head: DOMAIN, frame: ERD_DIFF_COLOUR.added });
    expect(look(dot, "Same")).toEqual({ head: DOMAIN, frame: QUIET_FRAME });
  });

  it("gives every header its kind's colour", () => {
    setErdPaint("kind", { core: KIND });
    expect(look(draw([table("Added", "added"), table("Same", "unchanged")]), "Same").head).toBe(KIND);
  });

  it("paints by kind in One too, the frame then in the header's colour", () => {
    setErdPaint("kind", { core: KIND });
    expect(look(draw([table("One")]), "One")).toEqual({ head: KIND, frame: KIND });
  });
});

describe("what the post-pass marks in Diff", () => {
  const tables = [table("Added", "added"), table("Inside", "unchanged", "changed"), table("Same", "unchanged")];

  it("fades the tables that did not change only while changes paint", () => {
    setErdPaint("change", {});
    expect([...erdDiffMarks(tables).faded]).toEqual(["Same"]);
    setErdPaint("domain", {});
    expect([...erdDiffMarks(tables).faded]).toEqual([]);
  });

  it("lays a halo under every table that changed, whatever paints", () => {
    setErdPaint("domain", {});
    expect([...erdDiffMarks(tables).halo]).toEqual([
      ["Added", ERD_DIFF_COLOUR.added],
      ["Inside", ERD_DIFF_COLOUR.changed],
    ]);
  });

});

describe("the choice of what paints", () => {
  it("keeps One's and Diff's choices apart, Diff starting by changes and One by domains", () => {
    const { result } = renderHook(() => useErdPaint());
    act(() => setPaintSections(["domains", "kinds", "changes"], true));
    expect(result.current.source).toBe("changes");
    act(() => setPaintSource("kinds"));
    act(() => setPaintSections(["domains", "kinds"], false));
    expect(result.current.source).toBe("domains");
    act(() => setPaintSections(["domains", "kinds", "changes"], true));
    expect(result.current.source).toBe("kinds");
  });

  it("falls back to the first section when the diagram does not offer the one chosen", () => {
    const { result } = renderHook(() => useErdPaint());
    act(() => setPaintSections(["domains", "kinds", "changes"], true));
    act(() => setPaintSource("changes"));
    act(() => setPaintSections(["domains"], true));
    expect(result.current.source).toBe("domains");
  });
});

describe("a specialization container in Diff", () => {
  const block = (diff?: ErdDiff) =>
    buildDotSource({ entities: [table("A", diff), table("B", diff)], relations: [], groups: [{ group_id: "g", label: "details", members: ["A", "B"] }] }, "gv-dot-lr");

  it("has no fill and an outline a point wider, so it does not stand out among the faded tables", () => {
    const dot = block("unchanged");
    expect(dot).toContain('style="rounded,dashed";');
    expect(dot).not.toContain("fillcolor=");
    expect(dot).toContain("penwidth=3;");
  });

  it("keeps its half-tone grey fill and its outline in One", () => {
    expect(block()).toContain('fillcolor="#0f172a0d"');
    expect(block()).toContain("penwidth=2;");
  });
});

