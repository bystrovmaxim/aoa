// src/lib/erdPostPass.test.ts
import { afterEach, describe, expect, it } from "vitest";
import type { ErdEntity } from "@/lib/buildDotSource";
import { addEdgeHitAreas, bindLineHover, focusTables, markRows, type ErdLineInfo } from "@/lib/erdPostPass";

// Markup shaped like Graphviz's: Player (0) has id, gender and an FK row named showcase twice
// (own row and FK row); Showcase (1) has id and players; Gender (2) has id.
const cell = (id: string, text: string, fill = "#ffffff") =>
  `<g id="a_${id}"><a xlink:title="t"><polygon fill="${fill}" stroke="none" points="0,0 1,0 1,1 0,1"/>` +
  `<text x="5" y="5" font-size="11.00">${text}</text></a></g>`;
const SVG = `
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><g class="graph">
<g id="node1" class="node"><title>Player</title>${cell("fn0_0", "id", "#fef9c3")}${cell("ft0_0", "str", "#fef9c3")}${cell("fn0_1", "showcase")}${cell("ft0_1", "ShowcaseCoreEntity")}${cell("fn0_2", "showcase", "#dbeafe")}${cell("ft0_2", "ShowcaseCoreEntity", "#dbeafe")}${cell("fn0_3", "gender")}${cell("ft0_3", "GenderEnumEntity")}</g>
<g id="node2" class="node"><title>Showcase</title>${cell("fn1_0", "id", "#fef9c3")}${cell("ft1_0", "str", "#fef9c3")}${cell("fn1_1", "players")}${cell("ft1_1", "PlayerCoreEntity")}${cell("fn1_2", "gender")}${cell("ft1_2", "GenderEnumEntity")}</g>
<g id="node3" class="node"><title>Gender</title>${cell("fn2_0", "id", "#fef9c3")}${cell("ft2_0", "str", "#fef9c3")}</g>
<g id="re0" class="edge"><title>Player&#45;&gt;Showcase</title><path fill="none" stroke="#94a3b8" d="M0,0C1,1 2,2 3,3"/><polygon fill="#94a3b8" stroke="#94a3b8" points="0,0 1,1 2,0"/><text>showcase</text></g>
<g id="re1" class="edge"><title>Player&#45;&gt;Gender</title><path fill="none" stroke="#94a3b8" d="M0,0C4,4 5,5 6,6"/><text>gender</text></g>
<g id="re2" class="edge"><title>Showcase&#45;&gt;Gender</title><path fill="none" stroke="#94a3b8" d="M0,0C7,7 8,8 9,9"/><text>gender</text></g>
</g></svg>`;

const entities: ErdEntity[] = [
  { id: "Player", fields: [{ name: "id", primary_key: true }, { name: "showcase" }, { name: "showcase", foreign_key: true }, { name: "gender" }] },
  { id: "Showcase", fields: [{ name: "id", primary_key: true }, { name: "players" }, { name: "gender" }] },
  { id: "Gender", fields: [{ name: "id", primary_key: true }] },
];
const relations: ErdLineInfo[] = [
  { source: "Player", target: "Showcase", relationship_kind: "association", source_field: "showcase", target_field: "players" },
  { source: "Player", target: "Gender", relationship_kind: "reference", source_field: "gender", target_field: null },
  { source: "Showcase", target: "Gender", relationship_kind: "reference", source_field: "gender", target_field: null },
];

function mount(): { root: HTMLElement; controller: AbortController } {
  document.body.innerHTML = `<div id="root">${SVG}</div>`;
  const root = document.getElementById("root")!;
  const controller = new AbortController();
  addEdgeHitAreas(root);
  bindLineHover(root, relations, entities, controller.signal);
  return { root, controller };
}
const text = (root: ParentNode, id: string) => root.querySelector(`g[id="a_${id}"] text`)!;
const polygonsSnapshot = (root: ParentNode) => [...root.querySelectorAll("polygon")].map((p) => p.outerHTML).join("");
const hover = (el: Element, on: boolean) => el.dispatchEvent(new MouseEvent(on ? "mouseenter" : "mouseleave"));

afterEach(() => {
  document.body.innerHTML = "";
});

describe("addEdgeHitAreas", () => {
  it("adds one transparent 10 px stroke per edge, along its path", () => {
    const { root } = mount();
    addEdgeHitAreas(root);

    const hits = root.querySelectorAll("path.erd-hit");
    expect(hits).toHaveLength(3);
    expect(hits[0]!.getAttribute("stroke")).toBe("transparent");
    expect(hits[0]!.getAttribute("stroke-width")).toBe("10");
    expect(hits[0]!.getAttribute("pointer-events")).toBe("stroke");
    expect(hits[0]!.getAttribute("d")).toBe("M0,0C1,1 2,2 3,3");
  });
});

describe("line hover", () => {
  it("raises the line, gives it the hovered class and marks both ends' rows by text only", () => {
    const { root } = mount();
    const before = polygonsSnapshot(root);
    const edge = root.querySelector('g[id="re0"]')!;

    hover(edge, true);

    expect(edge.classList.contains("is-hovered")).toBe(true);
    expect(edge.parentNode!.lastElementChild).toBe(edge);
    for (const id of ["fn0_1", "fn0_2", "fn1_1"]) {
      expect(text(root, id).getAttribute("font-weight")).toBe("bold");
      expect(text(root, id).getAttribute("fill")).toBe("#0f172a");
    }
    expect(text(root, "ft1_1").getAttribute("fill")).toBe("#334155");
    expect(text(root, "fn0_3").getAttribute("font-weight")).toBeNull();
    expect(polygonsSnapshot(root)).toBe(before);
  });

  it("marks the key row of the target when the relation has no inverse", () => {
    const { root } = mount();

    hover(root.querySelector('g[id="re1"]')!, true);

    expect(text(root, "fn0_3").getAttribute("font-weight")).toBe("bold");
    expect(text(root, "fn2_0").getAttribute("font-weight")).toBe("bold");
  });

  it("restores the text exactly when the pointer leaves", () => {
    const { root } = mount();
    const edge = root.querySelector('g[id="re0"]')!;
    const html = text(root, "fn0_1").outerHTML;

    hover(edge, true);
    hover(edge, false);

    expect(edge.classList.contains("is-hovered")).toBe(false);
    expect(text(root, "fn0_1").outerHTML).toBe(html);
  });

  it("emphasises every line of a hovered row and marks the rows at their ends", () => {
    const { root } = mount();

    hover(root.querySelector('g[id="a_fn0_0"]')!, true); // id: no line of its own
    expect(root.querySelectorAll("g.edge.is-hovered")).toHaveLength(0);

    hover(root.querySelector('g[id="a_fn2_0"]')!, true); // Gender's key: two gender lines point at it
    expect(root.querySelector('g[id="re1"]')!.classList.contains("is-hovered")).toBe(true);
    expect(root.querySelector('g[id="re2"]')!.classList.contains("is-hovered")).toBe(true);
    expect(text(root, "fn0_3").getAttribute("font-weight")).toBe("bold");
    expect(text(root, "fn1_2").getAttribute("font-weight")).toBe("bold");
    hover(root.querySelector('g[id="a_fn2_0"]')!, false);
    expect(root.querySelectorAll("g.edge.is-hovered")).toHaveLength(0);
    expect(text(root, "fn0_3").getAttribute("font-weight")).toBeNull();
  });

  it("leaves a press on a line to the canvas, so dragging from it still pans", () => {
    const { root } = mount();
    let reached = false;
    root.addEventListener("mousedown", () => {
      reached = true;
    });

    root.querySelector("path.erd-hit")!.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));

    expect(reached).toBe(true);
  });
});

describe("markRows", () => {
  it("keeps a bold type inside the table by growing it leftwards from its right edge", () => {
    const { root } = mount();
    const type = text(root, "ft1_1");
    Object.defineProperty(type, "getComputedTextLength", { value: () => 100 });
    const html = type.outerHTML;

    markRows(root, ["ft1_1"], true);
    expect(type.getAttribute("text-anchor")).toBe("end");
    expect(type.getAttribute("x")).toBe("105.00");

    markRows(root, ["ft1_1"], false);
    expect(type.outerHTML).toBe(html);
  });

  it("never touches a polygon", () => {
    const { root } = mount();
    const before = polygonsSnapshot(root);

    markRows(root, ["fn0_0", "ft0_0"], true);

    expect(polygonsSnapshot(root)).toBe(before);
  });
});

describe("which tables stay bright on hover (spec 029, FR-040, FR-041)", () => {
  const bright = (root: ParentNode) =>
    [...root.querySelectorAll<SVGElement>("g.node")].filter((n) => n.style.opacity === "1").map((n) => n.querySelector("title")!.textContent).sort();
  const brightLines = (root: ParentNode) =>
    [...root.querySelectorAll<SVGElement>("g.edge")].filter((e) => e.style.opacity === "1").map((e) => e.id).sort();

  it("a hovered table: itself and its lines, as before", () => {
    const { root } = mount();
    focusTables(root, new Set(["Player"]));
    expect(bright(root)).toEqual(["Player"]);
    expect(brightLines(root)).toEqual(["re0", "re1"]);
  });

  it("an FK row: its own table and the table its line joins", () => {
    const { root } = mount();
    focusTables(root, new Set(["Player"])); // the pointer is inside Player first
    hover(root.querySelector('g[id="a_fn0_2"]')!, true);
    expect(bright(root)).toEqual(["Player", "Showcase"]);
    expect(brightLines(root)).toEqual(["re0"]);
    hover(root.querySelector('g[id="a_fn0_2"]')!, false);
    expect(bright(root)).toEqual(["Player"]);
  });

  it("a PK row: every table whose lines point at it", () => {
    const { root } = mount();
    hover(root.querySelector('g[id="a_fn2_0"]')!, true);
    expect(bright(root)).toEqual(["Gender", "Player", "Showcase"]);
    expect(brightLines(root)).toEqual(["re1", "re2"]);
  });

  it("a line: the two tables it joins, and everything bright again when it is left", () => {
    const { root } = mount();
    const line = root.querySelector('g[id="re2"]')!;
    hover(line, true);
    expect(bright(root)).toEqual(["Gender", "Showcase"]);
    expect(brightLines(root)).toEqual(["re2"]);
    hover(line, false);
    expect(bright(root)).toEqual(["Gender", "Player", "Showcase"]);
  });
});
