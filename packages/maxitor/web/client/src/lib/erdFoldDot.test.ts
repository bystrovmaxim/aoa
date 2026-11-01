import { describe, expect, it } from "vitest";
import { buildBlockMeasureDot, buildDotSource, erdBlockWidths, type ErdEntity, type ErdFold } from "@/lib/buildDotSource";
import { placeKindIcons } from "@/lib/erdPostPass";

const entity: ErdEntity = { id: "t", label: "T", fields: [{ name: "id", primary_key: true }, { name: "plain" }, { name: "other" }] };
const fold = (collapsed: boolean, hidden = [1, 2]): ReadonlyMap<string, ErdFold> => new Map([["t", { hidden: new Set(hidden), collapsed }]]);
const dot = (folds?: ReadonlyMap<string, ErdFold>) => buildDotSource({ entities: [entity], relations: [], folds }, "gv-dot-lr");

describe("collapsed tables in the DOT (spec 043)", () => {
  it("hides the rows and says how many, keeping the others' indices", () => {
    const text = dot(fold(true, [1]));
    expect(text).not.toContain('ID="fn0_1"');
    expect(text).toContain('ID="fn0_2"');
    expect(text).toContain("1 field hidden");
  });

  it("says the plural", () => expect(dot(fold(true))).toContain("2 fields hidden"));

  it("draws every row of an expanded table, with the control", () => {
    const text = dot(fold(false));
    expect(text).toContain('ID="fn0_1"');
    expect(text).not.toContain("hidden</FONT>");
    expect(text).toContain('ID="cl0"');
  });

  it("has no control where nothing would hide", () => expect(dot(fold(false, []))).not.toContain('ID="cl0"'));

  it("differs from the old drawing only by the control (FR-031)", () => {
    expect(dot(fold(false)).replace(/<TD WIDTH="4"><\/TD><TD ID="cl0".*?<\/TD>/, "")).toBe(dot());
  });

  it("measures a collapsed table whole", () => {
    const text = buildBlockMeasureDot({ entities: [entity], relations: [], folds: fold(true) });
    expect(text).toContain('ID="fn0_1"');
    expect(text).not.toContain("hidden</FONT>");
  });

  it("keeps a collapsed table as wide as it is whole, and leaves an expanded one alone", () => {
    const svg = '<g id="node1"><title>t</title><g id="a_hd0"><polygon points="0,0 300.2,0 300.2,20 0,20"/></g></g>';
    expect(erdBlockWidths({ entities: [entity], relations: [], folds: fold(true) }, svg).get("t")).toBe(301);
    expect(erdBlockWidths({ entities: [entity], relations: [], folds: fold(false) }, svg).has("t")).toBe(false);
    expect(buildDotSource({ entities: [entity], relations: [], folds: fold(true) }, "gv-dot-lr", new Map([["t", 301]]))).toContain('WIDTH="301"');
  });
});

describe("the collapse control's chevron", () => {
  const svg = (
    '<g id="a_hd0"><a><polygon points="0,0 200,0 200,20 0,20"/></a></g>' +
    '<g id="a_ks0"><a><polygon points="4,2 20,2 20,18 4,18"/></a></g>' +
    '<g id="a_hn0"><a><polygon points="24,2 150,2 150,18 24,18"/><text x="30" y="14" font-size="12">T</text></a></g>' +
    '<g id="a_cl0"><a><polygon points="160,2 176,2 176,18 160,18"/></a></g>'
  );
  const chevron = (collapsed: boolean) => /erd-collapse-chevron"[^>]* d="M[\d.]+ ([\d.]+) L[\d.]+ ([\d.]+)/.exec(placeKindIcons(svg, [entity], () => "", fold(collapsed)))!;

  it("points up on a whole table and down on a collapsed one", () => {
    const [up, down] = [chevron(false), chevron(true)];
    expect(Number(up[2])).toBeLessThan(Number(up[1]));
    expect(Number(down[2])).toBeGreaterThan(Number(down[1]));
  });

  it("stands inside the control's group, so a click on it names the table", () => {
    const out = placeKindIcons(svg, [entity], () => "", fold(false));
    expect(out.indexOf("erd-collapse-hit")).toBeGreaterThan(out.indexOf('id="a_cl0"'));
  });
});
