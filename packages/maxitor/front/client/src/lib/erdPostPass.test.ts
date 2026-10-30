// src/lib/erdPostPass.test.ts
import { afterEach, describe, expect, it } from "vitest";
import type { ErdEntity } from "@/lib/buildDotSource";
import { addEdgeHitAreas, addEndLabelBadges, bindLineHover, END_LABEL_CLASS, erdEndLabelSx, focusTables, markRows, placeEndLabel, type Box, type ErdLineInfo } from "@/lib/erdPostPass";

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
  // Bright: lit by the hover, or back as drawn once it is left.
  const bright = (root: ParentNode) =>
    [...root.querySelectorAll<SVGElement>("g.node")].filter((n) => n.style.opacity === "1" || n.style.opacity === "").map((n) => n.querySelector("title")!.textContent).sort();
  const brightLines = (root: ParentNode) =>
    [...root.querySelectorAll<SVGElement>("g.edge")].filter((e) => e.style.opacity === "1").map((e) => e.id).sort();

  it("a hovered table: itself and its lines, as before", () => {
    const { root } = mount();
    focusTables(root, new Set(["Player"]));
    expect(bright(root)).toEqual(["Player"]);
    expect(brightLines(root)).toEqual(["re0", "re1"]);
  });

  it("scenario 1 — a table: the others dim, and every line not touching it", () => {
    const { root } = mount();
    focusTables(root, new Set(["Showcase"]));
    expect(bright(root)).toEqual(["Showcase"]);
    expect(brightLines(root)).toEqual(["re0", "re2"]);
  });

  it("scenario 2 — an FK row: its line bold, the joined table bright, the table's other lines as they are, the rest dim", () => {
    const { root } = mount();
    focusTables(root, new Set(["Player"])); // the pointer is inside Player first
    hover(root.querySelector('g[id="a_fn0_2"]')!, true);
    expect(bright(root)).toEqual(["Player", "Showcase"]);
    // Player's other line (re1, to Gender) stays bright and not bold; Showcase's line to Gender (re2) dims.
    expect(brightLines(root)).toEqual(["re0", "re1"]);
    expect([...root.querySelectorAll("g.edge.is-hovered")].map((e) => e.id)).toEqual(["re0"]);
    hover(root.querySelector('g[id="a_fn0_2"]')!, false);
    expect(bright(root)).toEqual(["Player"]);
    expect(brightLines(root)).toEqual(["re0", "re1"]);
  });

  it("a PK row: every table whose lines point at it", () => {
    const { root } = mount();
    hover(root.querySelector('g[id="a_fn2_0"]')!, true);
    expect(bright(root)).toEqual(["Gender", "Player", "Showcase"]);
    expect(brightLines(root)).toEqual(["re1", "re2"]);
    expect([...root.querySelectorAll("g.edge.is-hovered")].map((e) => e.id)).toEqual(["re1", "re2"]);
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

  it("gives every table back the opacity it was drawn with when the hover ends — a faded table stays faded (spec 038)", () => {
    const { root } = mount();
    const line = root.querySelector('g[id="re2"]')!;
    hover(line, true);
    hover(line, false);
    expect([...root.querySelectorAll<SVGElement>("g.node, g.edge")].map((element) => element.style.opacity)).toEqual(Array(root.querySelectorAll("g.node, g.edge").length).fill(""));
  });
});

describe("a line's end labels (spec 029, FR-042)", () => {
  // jsdom lays nothing out: a label's box is made up here, as a browser would measure it.
  const withBoxes = () => {
    Object.defineProperty(SVGElement.prototype, "getBBox", {
      configurable: true,
      value: () => ({ x: 10, y: 20, width: 40, height: 9 }),
    });
  };

  it("get a white plate under each label, once", () => {
    withBoxes();
    const { root } = mount();
    addEndLabelBadges(root);
    addEndLabelBadges(root);
    const labels = root.querySelectorAll("g.edge text");
    const plates = root.querySelectorAll(`g.edge rect.${END_LABEL_CLASS}`);
    expect(plates).toHaveLength(labels.length);
    expect(plates[0]!.nextElementSibling).toBe(labels[0]);
    expect([...plates].map((p) => [p.getAttribute("x"), p.getAttribute("width"), p.getAttribute("rx")])[0]).toEqual(["7", "46", "3"]);
  });

  it("are hidden until the line is hovered — by a mouse, a row, or a follower's replayed hover", () => {
    expect(erdEndLabelSx[`& g.edge text, & g.edge rect.${END_LABEL_CLASS}`]).toEqual({ visibility: "hidden" });
    expect(erdEndLabelSx[`& g.edge.is-hovered text, & g.edge.is-hovered rect.${END_LABEL_CLASS}`]).toEqual({ visibility: "visible" });
    const { root } = mount();
    const line = root.querySelector('g[id="re0"]')!;
    hover(line, true);
    expect(line.classList.contains("is-hovered")).toBe(true);
    hover(line, false);
    expect(line.classList.contains("is-hovered")).toBe(false);
  });
});

describe("where a line's end label goes (spec 029, FR-042)", () => {
  // A straight line leaving a table at (0, 0) to the right; the label names this end.
  const straight = (d: number) => ({ x: d, y: 0 });
  const plate = { width: 30, height: 10 };
  const table: Box = { x: -50, y: -20, width: 50, height: 40 };
  const overlaps = (a: Box, b: Box) => a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
  const offTheLine = (box: Box) => box.y + box.height <= 0 || box.y >= 0;

  it("stands clear of the table its line leaves, and beside the line, not on it", () => {
    const box = placeEndLabel(straight, 200, plate, [table]);
    expect(overlaps(box, table)).toBe(false);
    expect(offTheLine(box)).toBe(true);
  });

  it("moves along the line past another table in the way", () => {
    const inTheWay: Box = { x: 0, y: -30, width: 60, height: 60 };
    const box = placeEndLabel(straight, 300, plate, [table, inTheWay]);
    expect(overlaps(box, table) || overlaps(box, inTheWay)).toBe(false);
    expect(box.x).toBeGreaterThanOrEqual(60);
    expect(offTheLine(box)).toBe(true);
  });

  it("works for a line leaving downwards too", () => {
    const down = (d: number) => ({ x: 0, y: d });
    const above: Box = { x: -40, y: -40, width: 80, height: 40 };
    const box = placeEndLabel(down, 200, plate, [above]);
    expect(overlaps(box, above)).toBe(false);
    expect(box.x + box.width <= 0 || box.x >= 0).toBe(true);
  });
});

describe("a specialization head and its variants (FR-046)", () => {
  // Record (0) has id and its axis row pressing; FirstPress (1) and Repress (2) each have id and record,
  // the reverse field; Label (3) stands apart. Each variant has its dashed line to the head.
  const BLOCK_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><g class="graph">
<g id="node1" class="node"><title>Record</title>${cell("fn0_0", "id")}${cell("ft0_0", "str")}${cell("fn0_1", "pressing")}${cell("ft0_1", "Specialization 2+")}</g>
<g id="node2" class="node"><title>FirstPress</title>${cell("fn1_0", "id")}${cell("ft1_0", "str")}${cell("fn1_1", "record")}${cell("ft1_1", "RecordCoreEntity")}</g>
<g id="node3" class="node"><title>Repress</title>${cell("fn2_0", "id")}${cell("ft2_0", "str")}${cell("fn2_1", "record")}${cell("ft2_1", "RecordCoreEntity")}</g>
<g id="node4" class="node"><title>Label</title>${cell("fn3_0", "id")}${cell("ft3_0", "str")}</g>
<g id="re1" class="edge"><title>FirstPress&#45;&gt;Record</title><path fill="none" d="M0,0C1,1 2,2 3,3"/></g>
<g id="re2" class="edge"><title>Repress&#45;&gt;Record</title><path fill="none" d="M0,0C4,4 5,5 6,6"/></g>
</g></svg>`;
  const blockEntities: ErdEntity[] = [
    { id: "Record", fields: [{ name: "id", primary_key: true }, { name: "pressing", foreign_key: true }] },
    { id: "FirstPress", fields: [{ name: "id", primary_key: true }, { name: "record", foreign_key: true }] },
    { id: "Repress", fields: [{ name: "id", primary_key: true }, { name: "record", foreign_key: true }] },
    { id: "Label", fields: [{ name: "id", primary_key: true }] },
  ];
  // As the server sends them: the axis line into the block (not drawn), then one dashed line per variant.
  const blockRelations: ErdLineInfo[] = [
    { source: "Record", target: "Record:pressing", relationship_kind: "specialization" },
    { source: "FirstPress", target: "Record", relationship_kind: "generalization", source_field: "record", target_field: "pressing" },
    { source: "Repress", target: "Record", relationship_kind: "generalization", source_field: "record", target_field: "pressing" },
  ];
  const mountBlock = () => {
    document.body.innerHTML = `<div id="root">${BLOCK_SVG}</div>`;
    const root = document.getElementById("root")!;
    bindLineHover(root, blockRelations, blockEntities, new AbortController().signal);
    return root;
  };
  const bright = (root: ParentNode) =>
    [...root.querySelectorAll<SVGElement>("g.node")].filter((n) => n.style.opacity === "1").map((n) => n.querySelector("title")!.textContent);
  const bold = (root: ParentNode) => [...root.querySelectorAll("g.edge.is-hovered")].map((e) => e.id);

  it("hovering the head's axis row lights the head and every variant, their lines bold", () => {
    const root = mountBlock();
    hover(root.querySelector('g[id="a_fn0_1"]')!, true);
    expect(bright(root)).toEqual(["Record", "FirstPress", "Repress"]);
    expect(bold(root)).toEqual(["re1", "re2"]);
    expect(text(root, "fn1_1").getAttribute("font-weight")).toBe("bold");
  });

  it("hovering a variant's reverse row lights that variant and the head only", () => {
    const root = mountBlock();
    hover(root.querySelector('g[id="a_fn2_1"]')!, true);
    expect(bright(root)).toEqual(["Record", "Repress"]);
    expect(bold(root)).toEqual(["re2"]);
    expect(text(root, "fn0_1").getAttribute("font-weight")).toBe("bold");
  });

  it("hovering a dashed line marks the two fields it joins", () => {
    const root = mountBlock();
    hover(root.querySelector('g[id="re1"]')!, true);
    expect(bright(root)).toEqual(["Record", "FirstPress"]);
    expect(text(root, "fn1_1").getAttribute("font-weight")).toBe("bold");
    expect(text(root, "fn0_1").getAttribute("font-weight")).toBe("bold");
  });
});
