// src/lib/erdPostPass.ts
/**
 * ERD post-pass on Graphviz's SVG: what the DOT source reserves, this draws.
 *
 * ``buildDotSource`` gives every table's header a kind slot — a cell with an ``ID`` and a ``TOOLTIP``,
 * filled with the header colour so Graphviz emits its box as ``<g id="a_ks<table>">`` — beside the name
 * cell. Graphviz stretches the name cell to the header and centres the name in it; this pass puts the
 * glyph at the header's left, after a small inset, and the name right after it — the header of spec 028
 * (FR-110; mockup screen 21), left-aligned like the field names below. The slot reserves the room and gives the
 * height; the glyph is drawn white inside the slot's link element, so its tooltip (the kind's name)
 * still covers it.
 *
 * Like ``containNodeFills`` it works on the markup, not on the DOM, and imports no value, so the
 * drawing check runs this very function in plain Node; the glyph drawing is passed in.
 */

import { ERD_DIFF_COLOUR, erdHeadInk, type ErdEntity } from "@/lib/buildDotSource";

/** Draws a kind's glyph in a 24-unit box: ``(word, ink, strokeWidth) => inner SVG``. */
export type KindGlyphDrawer = (word: string, ink: string, strokeWidth: number) => string;

/** Stroke width of a header glyph, in the glyph's own 24-unit box. */
const HEADER_GLYPH_STROKE = 2.4;
/** Space between the glyph and the name, in points (the spacer cell of the header). */
const HEADER_GLYPH_GAP = 4;
/** Space between the header's left edge and the glyph, in points (the mockup's 12 of a 250 card). */
export const HEADER_INSET_PT = 10;
/**
 * Half the height of a capital of Helvetica, as a share of the font size (its cap height is 0.718 em):
 * how far above its baseline a name's visual middle stands.
 */
export const CAP_HALF_EM = 0.359;

/**
 * The box of a cell's ``points`` polygon inside its ``<g id="a_<id>">``, or ``null``. A cell that holds a
 * nested table (the header) is closed by its last ``</a>`` before the next cell's group, hence ``outer``.
 */
function cellBox(
  markup: string,
  cellId: string,
  outer = false,
): { x: number; y: number; right: number; bottom: number; size: number; end: number } | null {
  const start = markup.indexOf(`<g id="a_${cellId}">`);
  if (start < 0) return null;
  const close = markup.indexOf("</a>", start);
  const match = /points="([^"]+)"/.exec(markup.slice(start, outer ? markup.indexOf("</g>", start) : close));
  if (!match) return null;
  const xs: number[] = [];
  const ys: number[] = [];
  for (const pair of match[1]!.trim().split(/\s+/)) {
    const [x, y] = pair.split(",").map(Number);
    if (Number.isFinite(x) && Number.isFinite(y)) {
      xs.push(x!);
      ys.push(y!);
    }
  }
  if (!xs.length) return null;
  const x = Math.min(...xs);
  const y = Math.min(...ys);
  const size = Math.min(Math.max(...xs) - x, Math.max(...ys) - y);
  return { x, y, right: Math.max(...xs), bottom: Math.max(...ys), size, end: close };
}

type Attribute = { at: number; length: number };

/** The first ``<text>`` inside ``<g id="a_<id>">``: where its ``x`` and ``y`` attributes sit, and its font size. */
function textPlace(markup: string, cellId: string): { x: Attribute; y: Attribute; fontSize: number } | null {
  const start = markup.indexOf(`<g id="a_${cellId}">`);
  if (start < 0) return null;
  const tag = /<text\b[^>]*>/.exec(markup.slice(start));
  if (!tag) return null;
  const find = (name: string): Attribute | null => {
    const attr = new RegExp(` ${name}="[-\\d.]+"`).exec(tag[0]);
    return attr ? { at: start + tag.index + attr.index, length: attr[0].length } : null;
  };
  const x = find("x");
  const y = find("y");
  const fontSize = Number(/ font-size="([\d.]+)"/.exec(tag[0])?.[1]);
  return x && y && fontSize > 0 ? { x, y, fontSize } : null;
}

/**
 * Draw each table's kind glyph at the left of its header, after the inset, and its name right after it,
 * both on one axis — the middle of the header band: the glyph's centre on it, and the name's capitals
 * centred on it (spec 029, FR-033). ``entities`` is the list the DOT was built from (its order gives the
 * cell ids).
 */
export function placeKindIcons(markup: string, entities: readonly ErdEntity[], drawGlyph: KindGlyphDrawer): string {
  const edits: Array<{ at: number; remove: number; text: string }> = [];
  entities.forEach((entity, table) => {
    const slot = cellBox(markup, `ks${table}`);
    const header = cellBox(markup, `hd${table}`, true);
    const nameCell = cellBox(markup, `hn${table}`, true);
    const name = textPlace(markup, `hn${table}`);
    if (!slot || slot.size <= 0 || !header || !nameCell || !name) return;
    const iconX = header.x + HEADER_INSET_PT;
    const textX = iconX + slot.size + HEADER_GLYPH_GAP;
    const axis = (header.y + header.bottom) / 2;
    const iconY = axis - slot.size / 2;
    const textY = axis + CAP_HALF_EM * name.fontSize;
    const kind = entity.entity_kind?.trim() || "unknown";
    edits.push({ at: name.y.at, remove: name.y.length, text: ` y="${textY.toFixed(2)}"` });
    edits.push({ at: name.x.at, remove: name.x.length, text: ` x="${textX.toFixed(2)}"` });
    edits.push({
      at: slot.end,
      remove: 0,
      text:
        `<g class="erd-kind-icon" pointer-events="none" transform="translate(${iconX.toFixed(2)},${iconY.toFixed(2)}) ` +
        `scale(${(slot.size / 24).toFixed(4)})">${drawGlyph(kind, erdHeadInk(entity), HEADER_GLYPH_STROKE)}</g>`,
    });
  });
  let out = markup;
  for (const { at, remove, text } of edits.sort((a, b) => b.at - a.at)) {
    out = out.slice(0, at) + text + out.slice(at + remove);
  }
  return out;
}

// ── Line hover ──────────────────────────────────────────────────────────────
// The rest of this module works on the live SVG once it is on the page: a wide invisible stroke so a
// 1 px line is easy to catch, the hovered look as a class (styled by the canvas), and the rows a line
// stands for marked by their text only — never their fill, border or size.

/** What the post-pass needs of a relation: its ends and the fields at them (``ErdRelation`` fits). */
export type ErdLineInfo = {
  source: string;
  target: string;
  relationship_kind?: string;
  source_field?: string | null;
  target_field?: string | null;
};

/** The class the hovered look hangs on. */
export const EDGE_HOVER_CLASS = "is-hovered";
const MARK_NAME_FILL = "#0f172a";
const MARK_TYPE_FILL = "#334155";

/** Give every edge an invisible stroke about 10 px wide along its path, so the pointer catches it. */
export function addEdgeHitAreas(root: ParentNode): void {
  root.querySelectorAll("g.edge").forEach((edge) => {
    if (edge.querySelector("path.erd-hit")) return;
    const path = edge.querySelector("path");
    if (!path) return;
    const hit = path.cloneNode(false) as Element;
    hit.setAttribute("class", "erd-hit");
    hit.setAttribute("fill", "none");
    hit.setAttribute("stroke", "transparent");
    hit.setAttribute("stroke-width", "10");
    hit.setAttribute("pointer-events", "stroke");
    path.parentNode!.insertBefore(hit, path);
  });
}

/** The class of the plate under a line's end label. */
export const END_LABEL_CLASS = "erd-end-label";

/**
 * Put a white plate under every label of a line — the field names at its ends — so a label reads over a
 * table it crosses (spec 029, FR-042). The labels and their plates show only while the line is hovered
 * (``erdEndLabelSx``); a line's own hover, a row's hover and a follower's replayed hover all set it.
 */
export function addEndLabelBadges(root: ParentNode): void {
  const tables = [...root.querySelectorAll<SVGGraphicsElement>("g.node")].map((node) => node.getBBox());
  root.querySelectorAll<SVGTextElement>("g.edge text").forEach((label) => {
    if (label.previousElementSibling?.classList.contains(END_LABEL_CLASS)) return;
    const box = label.getBBox();
    if (!(box.width > 0)) return;
    const size = { width: box.width + 6, height: box.height + 2 };
    let place: Box = { x: box.x - 3, y: box.y - 1, ...size };
    // Graphviz sets a label at its line's end, often on the table there; it moves along the line, clear.
    const line = label.closest("g.edge")?.querySelector<SVGPathElement>("path:not(.erd-hit)");
    if (line && typeof line.getTotalLength === "function") {
      const length = line.getTotalLength();
      const start = line.getPointAtLength(0);
      const end = line.getPointAtLength(length);
      const centre = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
      const atEnd = Math.hypot(centre.x - end.x, centre.y - end.y) < Math.hypot(centre.x - start.x, centre.y - start.y);
      place = placeEndLabel((d) => line.getPointAtLength(atEnd ? length - d : d), length, size, tables);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("x", String(place.x + place.width / 2));
      // The baseline that centres the text on its plate: the middle plus a third of the font size.
      const fontSize = Number(label.getAttribute("font-size")) || box.height * 0.8;
      label.setAttribute("y", String(place.y + place.height / 2 + fontSize * 0.35));
    }
    const plate = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    plate.setAttribute("class", END_LABEL_CLASS);
    plate.setAttribute("x", String(place.x));
    plate.setAttribute("y", String(place.y));
    plate.setAttribute("width", String(place.width));
    plate.setAttribute("height", String(place.height));
    plate.setAttribute("rx", "3");
    label.parentNode!.insertBefore(plate, label);
  });
}

/** A box in the drawing's units. */
export type Box = { x: number; y: number; width: number; height: number };

const overlaps = (a: Box, b: Box) => a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;

/** Space between a label's plate and its line, and the step it moves along the line, in drawing units. */
const LABEL_OFFSET = 4;
const LABEL_STEP = 3;

/**
 * Where an end label's plate goes (spec 029, FR-042): walking along its line from the end it names
 * (``pointAt(0)`` is that end, ``pointAt(length)`` the other), the first place where the plate — set
 * beside the line, off it, on whichever side is clear — touches none of ``tables``. Not past the line's
 * middle; when nowhere is clear, the last place tried.
 */
export function placeEndLabel(
  pointAt: (distance: number) => { x: number; y: number },
  length: number,
  plate: { width: number; height: number },
  tables: readonly Box[],
): Box {
  const half = Math.max(plate.width, plate.height) / 2 + LABEL_OFFSET;
  let last: Box | null = null;
  for (let along = half; along <= Math.max(half, length / 2); along += LABEL_STEP) {
    const p = pointAt(along);
    const q = pointAt(Math.min(length, along + 1));
    const dx = q.x - p.x;
    const dy = q.y - p.y;
    const norm = Math.hypot(dx, dy) || 1;
    // Off the line: the plate's centre moved across it by half the plate's extent plus a gap.
    const across = Math.abs((plate.width / 2) * (dy / norm)) + Math.abs((plate.height / 2) * (dx / norm)) + LABEL_OFFSET;
    for (const side of [1, -1]) {
      const cx = p.x + side * (-dy / norm) * across;
      const cy = p.y + side * (dx / norm) * across;
      const box = { x: cx - plate.width / 2, y: cy - plate.height / 2, width: plate.width, height: plate.height };
      last = box;
      if (!tables.some((table) => overlaps(box, table))) return box;
    }
  }
  return last ?? { x: pointAt(0).x - plate.width / 2, y: pointAt(0).y - plate.height / 2, ...plate };
}

/** The ink a hovered grey line takes. */
const HOVERED_LINE_INK = "#475569";

/**
 * The canvas's style for a hovered line (or every line of a hovered row): thicker, a grey one darker. A line painted by
 * its change in Diff keeps its colour — the hover never says a removed line is something else (spec 038).
 */
export const erdLineHoverSx = {
  "& g.edge path": { transition: "stroke-width 100ms ease, stroke 100ms ease" },
  [`& g.edge.${EDGE_HOVER_CLASS} path:not(.erd-hit)`]: { stroke: HOVERED_LINE_INK, strokeWidth: 2.4 },
  [`& g.edge.${EDGE_HOVER_CLASS} polygon`]: { stroke: HOVERED_LINE_INK },
  [`& g.edge.${EDGE_HOVER_CLASS} polygon:not([fill='none'])`]: { fill: HOVERED_LINE_INK },
  [`& g.edge.${EDGE_HOVER_CLASS} text`]: { fill: "#334155", fontWeight: 700 },
  ...Object.fromEntries(
    Object.values(ERD_DIFF_COLOUR).flatMap((colour) => [
      [`& g.edge.${EDGE_HOVER_CLASS} path[stroke='${colour}']:not(.erd-hit), & g.edge.${EDGE_HOVER_CLASS} polygon[stroke='${colour}']`, { stroke: colour }],
      [`& g.edge.${EDGE_HOVER_CLASS} polygon[fill='${colour}']`, { fill: colour }],
    ]),
  ),
} as const;

/** The canvas's style for line labels: hidden, and shown on their plates while the line is hovered. */
export const erdEndLabelSx = {
  [`& g.edge text, & g.edge rect.${END_LABEL_CLASS}`]: { visibility: "hidden" },
  [`& g.edge.${EDGE_HOVER_CLASS} text, & g.edge.${EDGE_HOVER_CLASS} rect.${END_LABEL_CLASS}`]: { visibility: "visible" },
  [`& rect.${END_LABEL_CLASS}`]: { fill: "#ffffff", stroke: "#cbd5e1", strokeWidth: 0.8 },
} as const;

/** Cell ids of the rows a relation stands for, at both ends. */
function rowsOf(line: ErdLineInfo, tables: Map<string, { index: number; fields: ErdEntity["fields"] }>): string[] {
  const cells: string[] = [];
  const add = (tableId: string, match: (field: NonNullable<ErdEntity["fields"]>[number]) => boolean) => {
    const table = tables.get(tableId);
    (table?.fields ?? []).forEach((field, row) => {
      if (match(field)) cells.push(`fn${table!.index}_${row}`, `ft${table!.index}_${row}`);
    });
  };
  if (!line.source_field) return cells;
  add(line.source, (f) => f.name === line.source_field);
  // Without an inverse, the far end is the key the field points at.
  if (line.target_field) add(line.target, (f) => f.name === line.target_field);
  else add(line.target, (f) => Boolean(f.primary_key));
  return cells;
}

/** Attributes a mark changes, saved on the text so leaving restores them exactly. */
const MARKED_ATTRIBUTES = ["font-weight", "fill", "text-anchor", "x"] as const;

/** Mark (or restore) the text of the given cells: bold and darker, the cell itself untouched. */
export function markRows(root: ParentNode, cells: readonly string[], on: boolean): void {
  for (const id of cells) {
    root.querySelectorAll(`g[id="a_${id}"] text`).forEach((text) => {
      if (on) {
        if (!text.hasAttribute("data-erd-mark")) {
          text.setAttribute("data-erd-mark", JSON.stringify(MARKED_ATTRIBUTES.map((name) => text.getAttribute(name))));
          // A type sits on the right edge; bold text is wider, so it grows leftwards from that edge
          // instead of running out of the table.
          const measure = (text as SVGTextContentElement).getComputedTextLength;
          if (id.startsWith("ft") && typeof measure === "function") {
            const right = Number(text.getAttribute("x")) + measure.call(text);
            text.setAttribute("text-anchor", "end");
            text.setAttribute("x", right.toFixed(2));
          }
        }
        text.setAttribute("font-weight", "bold");
        text.setAttribute("fill", id.startsWith("fn") ? MARK_NAME_FILL : MARK_TYPE_FILL);
        return;
      }
      const saved = text.getAttribute("data-erd-mark");
      if (saved === null) return;
      const values = JSON.parse(saved) as Array<string | null>;
      MARKED_ATTRIBUTES.forEach((name, i) => {
        const value = values[i];
        if (value === null || value === undefined) text.removeAttribute(name);
        else text.setAttribute(name, value);
      });
      text.removeAttribute("data-erd-mark");
    });
  }
}

/**
 * Line hover in both directions. Hovering a line gives it the hovered look, raises it above the lines it
 * crosses and marks the rows of its fields in both tables; hovering a row whose field has lines does the
 * same for every one of them. Either way the tables they join stay bright and the rest dim; on a row, the
 * hovered table's other lines stay as they are (spec 029, FR-041). ``relations[k]`` is the line Graphviz wrote as ``<g id="re<k>">``.
 */
/** A table's id: the text of its node's ``<title>``. */
function tableOf(node: Element): string {
  return node.querySelector(":scope > title")?.textContent?.trim() ?? "";
}

/**
 * Keep ``tables`` bright and dim every other table; keep bright the lines in ``lines`` — or, when none are
 * given, every line touching a kept table — and dim the rest. The look of a hovered table, a hovered key
 * row and a hovered line alike (spec 029, FR-040, FR-041).
 */
export function focusTables(root: ParentNode, tables: ReadonlySet<string>, lines?: ReadonlySet<Element>): void {
  root.querySelectorAll<SVGElement>("g.node").forEach((node) => {
    node.style.opacity = tables.has(tableOf(node)) ? "1" : "0.35";
  });
  root.querySelectorAll<SVGElement>("g.edge").forEach((edge) => {
    const title = edge.querySelector(":scope > title")?.textContent?.trim() ?? "";
    const kept = lines ? lines.has(edge) : [...tables].some((table) => title.includes(table));
    edge.style.opacity = kept ? "1" : "0.2";
  });
}

/** Every table and line as drawn again — a table Diff fades stays faded. */
export function clearTableFocus(root: ParentNode): void {
  root.querySelectorAll<SVGElement>("g.node, g.edge").forEach((element) => {
    element.style.opacity = "";
  });
}

export function bindLineHover(
  root: ParentNode,
  relations: readonly ErdLineInfo[],
  entities: readonly ErdEntity[],
  signal: AbortSignal,
): void {
  const tables = new Map(entities.map((e, index) => [e.id, { index, fields: e.fields }]));
  const edgeRows = relations.map((line) => rowsOf(line, tables));
  const show = (edges: Element[], on: boolean) => {
    for (const edge of edges) {
      const k = Number(edge.id.slice(2));
      edge.classList.toggle(EDGE_HOVER_CLASS, on);
      if (on && edge.parentNode && edge.parentNode.lastElementChild !== edge) edge.parentNode.appendChild(edge);
      markRows(root, edgeRows[k] ?? [], on);
    }
  };
  const edgesById = (ids: number[]) => ids.map((k) => root.querySelector(`g[id="re${k}"]`)).filter((e): e is Element => e !== null);
  // Every line one of whose ends is ``table``.
  const touching = (table: string) =>
    new Set(edgesById(relations.flatMap((line, k) => (line.source === table || line.target === table ? [k] : []))));
  // The tables a set of lines joins: both ends of each.
  const joined = (edges: Element[]) => new Set(edges.flatMap((edge) => {
    const line = relations[Number(edge.id.slice(2))];
    return line ? [line.source, line.target] : [];
  }));

  root.querySelectorAll('g.edge[id^="re"]').forEach((edge) => {
    edge.addEventListener("mouseenter", () => {
      show([edge], true);
      focusTables(root, joined([edge]), new Set([edge]));
    }, { signal });
    edge.addEventListener("mouseleave", () => {
      show([edge], false);
      clearTableFocus(root);
    }, { signal });
  });

  // A row's lines: every line one of whose ends is this row.
  const rowLines = new Map<string, number[]>();
  edgeRows.forEach((cells, k) => {
    for (const cell of cells) {
      const row = cell.slice(2);
      rowLines.set(row, [...(rowLines.get(row) ?? []), k]);
    }
  });
  root.querySelectorAll('g[id^="a_fn"], g[id^="a_ft"]').forEach((cell) => {
    const lines = rowLines.get(cell.id.slice(4)) ?? [];
    if (!lines.length) return;
    // The row's own table stays the hovered one; its lines and every table they join are lit with it.
    const own = tableOf(cell.closest("g.node") ?? cell);
    cell.addEventListener("mouseenter", () => {
      const edges = edgesById(lines);
      // Scenario 2 (maintainer, 2026-10-27): the field's lines go bold (``show``); the tables they join
      // stay bright; the hovered table's other lines stay as they are; every other line and table dims.
      show(edges, true);
      focusTables(root, new Set([own, ...joined(edges)]), touching(own));
    }, { signal });
    cell.addEventListener("mouseleave", () => {
      show(edgesById(lines), false);
      focusTables(root, new Set([own]));
    }, { signal });
  });
}

// ── The card as designed ─────────────────────────────────────────────────

/** A node's markup: from its ``<g id="node…" class="node">`` to the next node or edge group. */
const NODE_START = /<g id="node\d+" class="node"[^>]*>/g;
const BACKDROP = /<path fill="white" stroke="none" d="([^"]+)"\/?>(?:<\/path>)?/;
const GROUP_START = /<g id="[^"]+" class="(?:node|edge|cluster)"/g;
const NUMBER = /-?\d+(?:\.\d+)?/g;

/** A number as the markup writes it: at most two decimals. */
function fixed(value: number): string {
  return String(Number(value.toFixed(2)));
}

/** The rectangle a Graphviz rounded outline spans, from its path. */
function spanOf(d: string): { x0: number; y0: number; x1: number; y1: number } | null {
  const values = (d.match(NUMBER) ?? []).map(Number);
  const xs = values.filter((_, i) => i % 2 === 0);
  const ys = values.filter((_, i) => i % 2 === 1);
  if (!xs.length || !ys.length) return null;
  return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) };
}

/** Move a fill's edges that stop just inside the card onto the card's edges, so nothing is left between them. */
function reachEdges(points: string, span: { x0: number; y0: number; x1: number; y1: number }, inset: number): string {
  const near = (value: number, edge: number) => Math.abs(value - edge) <= inset + 0.01;
  const values = (points.match(NUMBER) ?? []).map(Number);
  return values
    .map((value, i) => {
      if (i % 2 === 0) return fixed(near(value, span.x0) ? span.x0 : near(value, span.x1) ? span.x1 : value);
      return fixed(near(value, span.y0) ? span.y0 : near(value, span.y1) ? span.y1 : value);
    })
    .reduce<string[]>((pairs, value, i, all) => (i % 2 === 0 ? [...pairs, `${value},${all[i + 1]}`] : pairs), [])
    .join(" ");
}

/** The opacity of a table that did not change, in Diff (spec 038, FR-022). */
export const ERD_FADED_OPACITY = 0.32;

/** The dash of a removed table's frame, in Diff. */
export const ERD_REMOVED_DASH = "5 3";

/** What Diff adds to the cards, by table id: the tables to fade and those whose frame is dashed. */
export type ErdCardMarks = { faded: ReadonlySet<string>; dashed: ReadonlySet<string>; halo?: ReadonlyMap<string, string> };

/** One node's markup drawn as the designed card, or as it was when it is not a card. */
function drawCard(node: string, radius: number, stroke: number, dashed = false): string {
  const backdrop = BACKDROP.exec(node);
  const span = backdrop ? spanOf(backdrop[1]!) : null;
  if (!backdrop || !span) return node;
  const d = backdrop[1]!;
  const box = `x="${fixed(span.x0)}" y="${fixed(span.y0)}" width="${fixed(span.x1 - span.x0)}" height="${fixed(span.y1 - span.y0)}" rx="${radius}"`;
  // Graphviz keeps its fills one unit inside its own outline.
  const inset = 1;
  let out = node.replace(backdrop[0], `<rect fill="white" stroke="none" ${box}/>`);
  out = out.replace(/(<clipPath id="[^"]+">)<rect [^>]*\/>/, `$1<rect ${box}/>`);
  const clip = /<clipPath id="([^"]+)">/.exec(out)?.[1];
  out = out.replace(/<polygon\b([^>]*)\bpoints="([^"]+)"/g, (_whole, attributes: string, points: string) => {
    const clipped = clip && !attributes.includes("clip-path") ? ` clip-path="url(#${clip})"` : "";
    return `<polygon${clipped}${attributes}points="${reachEdges(points, span, inset)}"`;
  });
  const outline = new RegExp(`<path fill="none" stroke="([^"]+)" d="${d.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"\\/?>(?:<\\/path>)?`);
  const dash = dashed ? ` stroke-dasharray="${ERD_REMOVED_DASH}"` : "";
  return out.replace(outline, (_, colour: string) => `<rect fill="none" stroke="${colour}" stroke-width="${stroke}"${dash} ${box}/>`);
}

/** The table id a node's markup draws: its ``<title>``, unescaped. */
function titleOf(node: string): string {
  return (/<title>([^<]*)<\/title>/.exec(node)?.[1] ?? "").replace(/&#45;/g, "-").replace(/&amp;/g, "&");
}

/**
 * Draw every ERD table as the card of spec 029 (FR-032): Graphviz's rounded outline and backdrop give
 * way to one rounded rectangle of ``radius`` (the mockup's 9) with a ``stroke``-wide outline in the
 * domain colour; the header and the row tints reach the card's edge and are trimmed to the same
 * rounded shape, so the header fills right up to the outline with no gap. Graphviz's layout — every
 * cell's place and size — is left as it is. Run after ``containNodeFills``. In Diff (spec 038) ``marks`` fades the
 * tables that did not change and dashes the frame of those that are gone.
 */
export function drawErdCards(svg: string, radius: number, stroke: number, marks?: ErdCardMarks): string {
  const starts = [...svg.matchAll(NODE_START)].map((m) => m.index ?? 0);
  if (!starts.length) return svg;
  let out = svg.slice(0, starts[0]);
  starts.forEach((start, i) => {
    const next = starts[i + 1] ?? svg.length;
    // A card ends where the next group of the drawing begins — a line (``re<k>``), a cluster or a node.
    GROUP_START.lastIndex = start + 1;
    const following = GROUP_START.exec(svg)?.index ?? svg.length;
    const end = Math.min(following, next);
    const node = svg.slice(start, end);
    const table = marks ? titleOf(node) : "";
    let drawn = drawCard(node, radius, stroke, marks?.dashed.has(table) ?? false);
    if (marks?.faded.has(table)) drawn = drawn.replace(/^<g id="node\d+" class="node"/, (head) => `${head} opacity="${ERD_FADED_OPACITY}"`);
    // a soft halo in the status colour under a table that changed, drawn first so the card stands on it.
    const haloColour = marks?.halo?.get(table);
    const card = haloColour ? /<rect fill="white" stroke="none" x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"/.exec(drawn) : null;
    if (haloColour && card) {
      const [x, y, w, h] = card.slice(1).map(Number);
      const pad = 40;
      const haloRect = `<rect x="${x - pad}" y="${y - pad}" width="${w + 2 * pad}" height="${h + 2 * pad}" rx="${pad + 6}" fill="${haloColour}" fill-opacity="0.16" filter="url(#erd-halo)"/>`;
      drawn = drawn.replace(/^(<g id="node\d+" class="node"[^>]*>)/, `$1${haloRect}`);
    }
    out += drawn + svg.slice(end, next);
  });
  // the halo's blur, once per drawing.
  return marks?.halo?.size ? out.replace(/(<svg\b[^>]*>)/, `$1<defs><filter id="erd-halo" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="22"/></filter></defs>`) : out;
}
