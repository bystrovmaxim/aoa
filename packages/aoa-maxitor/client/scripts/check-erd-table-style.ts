// scripts/check-erd-table-style.ts
/**
 * The ERD table style of spec 028 (FR-110 … FR-115; mockup screen 21) — what one table and one line
 * look like in the SVG the page shows.
 *
 * It renders a fixture through the same WASM Graphviz build the client loads, runs the production
 * passes (`containNodeFills`, `drawErdCards`, `placeKindIcons`) over the drawing, and asserts each rule: the header in
 * the domain colour, flush with the frame and as high as the mockup's, its name white, bold and at the
 * left; the frame in the domain colour around a white body; every second row tinted at 6 %; PK and FK
 * in their colours in a column of their own; the type smaller, grey and on the right; grey lines, a
 * dashed generalization that ends in ERD bars, not an arrowhead. It is plain Node: no framework, no bundler.
 *
 * Exit codes: 0 all assertions passed; 1 an assertion failed; 2 the environment cannot run it.
 */

import { Graphviz } from "@hpcc-js/wasm-graphviz";
import {
  buildDotSource,
  buildErdDot,
  ERD_FK_COLOUR,
  ERD_CARD_RADIUS,
  ERD_CARD_STROKE,
  ERD_HEADER_HEIGHT_PT,
  ERD_PK_COLOUR,
  ERD_ROW_HEIGHT_PT,
  ERD_TYPE_COLOUR,
  type ErdGraphPayload,
} from "../src/lib/buildDotSource.ts";
import { containNodeFills } from "../src/lib/containNodeFills.ts";
import { CAP_HALF_EM, drawErdCards, HEADER_INSET_PT, placeKindIcons } from "../src/lib/erdPostPass.ts";
import { kindGlyphSvg } from "../src/lib/icons/entity_kind_glyphs.ts";

let failures = 0;

/** Record one assertion. */
function check(label: string, passed: boolean, detail = ""): void {
  if (passed) {
    console.log(`ok   ${label}`);
  } else {
    failures += 1;
    console.error(`FAIL ${label}${detail ? ` — ${detail}` : ""}`);
  }
}

let gv: Awaited<ReturnType<typeof Graphviz.load>>;
try {
  gv = await Graphviz.load();
} catch (error) {
  console.error(`cannot load WASM Graphviz: ${String(error)}`);
  process.exit(2);
}

const COLOUR = "#10b981";
const field = (name: string, type: string, extra: Record<string, unknown> = {}) => ({ name, type, primary_key: false, foreign_key: false, ...extra });
const fixture: ErdGraphPayload = {
  entities: [
    {
      id: "shop.PlayerCoreEntity",
      label: "PlayerCoreEntity",
      color: COLOUR,
      entity_kind: "core",
      fields: [{ ...field("id", "str"), primary_key: true }, field("username", "str"), { ...field("showcase", "ShowcaseCoreEntity"), foreign_key: true }, field("region", "str | None")],
    },
    { id: "shop.BaseEntity", label: "BaseEntity", color: "#3b82f6", entity_kind: "core", fields: [{ ...field("id", "str"), primary_key: true }] },
  ],
  relations: [{ source: "shop.PlayerCoreEntity", target: "shop.BaseEntity", label: "", relationship_kind: "generalization", source_cardinality: "zero_one", target_cardinality: "one" }],
};

const svg = placeKindIcons(
  drawErdCards(containNodeFills(gv.layout(buildErdDot(fixture, "gv-dot-lr", (measureDot) => gv.layout(measureDot, "svg", "dot")), "svg", "dot")), ERD_CARD_RADIUS, ERD_CARD_STROKE),
  fixture.entities,
  kindGlyphSvg,
);
const table = svg.slice(svg.indexOf("<title>shop.PlayerCoreEntity</title>"), svg.indexOf("<!-- shop.BaseEntity -->"));

/** The y-extent of a ``points`` polygon. */
function heightOf(points: string): number {
  const ys = points.trim().split(/\s+/).map((pair) => Number(pair.split(",")[1]));
  return Math.max(...ys) - Math.min(...ys);
}

/** The cell group ``a_<id>`` of the table. */
function cell(id: string): string {
  const start = table.indexOf(`<g id="a_${id}">`);
  return start < 0 ? "" : table.slice(start, table.indexOf("</g>", start));
}

// ── FR-110: header ───────────────────────────────────────────────────────────
const header = /<g id="a_hd0">[\s\S]*?<polygon clip-path="url\(#[^"]+\)" fill="([^"]+)"[^>]* points="([^"]+)"/.exec(table);
check("FR-110 header is filled with the domain colour and trimmed to the frame's rounded corners", header?.[1] === COLOUR);
// The header band is 30 high and, since spec 029, also fills the unit under the outline above it.
check(`FR-110 header is ${ERD_HEADER_HEIGHT_PT} high`, header !== null && Math.abs(heightOf(header[2]!) - (ERD_HEADER_HEIGHT_PT + 1)) < 0.6, header ? `${heightOf(header[2]!)}` : "no header");
const headerLeft = header ? Math.min(...header[2]!.trim().split(/\s+/).map((pair) => Number(pair.split(",")[0]))) : NaN;
const frame = new RegExp(`<rect fill="none" stroke="${COLOUR}" stroke-width="([\\d.]+)" x="([-\\d.]+)" y="([-\\d.]+)" width="([\\d.]+)" height="([\\d.]+)" rx="([\\d.]+)"/>`).exec(table);
const frameLeft = Number(frame?.[2]);
const frameTop = Number(frame?.[3]);
const headerTop = header ? Math.min(...header[2]!.trim().split(/\s+/).map((pair) => Number(pair.split(",")[1]))) : NaN;
// Spec 029, FR-032 / SC-007: the header fills right up to the outline — no gap at the side or the top.
check("029 FR-032 header reaches the outline with no gap", Math.abs(headerLeft - frameLeft) < 0.01 && Math.abs(headerTop - frameTop) < 0.01, `header ${headerLeft},${headerTop}, frame ${frameLeft},${frameTop}`);
const name = /<g id="a_hn0">[\s\S]*?<text[^>]* x="([-\d.]+)"[^>]*font-weight="bold"[^>]*fill="white">PlayerCoreEntity<\/text>/.exec(table);
check("FR-110 entity name is white and bold", name !== null);
const icon = Number(/class="erd-kind-icon"[^>]*translate\(([-\d.]+),/.exec(table)?.[1]);
check("FR-110 entity name is left-aligned, after the kind icon", Math.abs(icon - (headerLeft + HEADER_INSET_PT)) < 0.6 && name !== null && Number(name[1]) < headerLeft + 40, `icon ${icon}, name ${name?.[1]}`);

// ── 029 FR-033: the kind icon and the name on one axis ───────────────────────
// For every table: the glyph's centre, the middle of the name's capitals and the middle of the header
// band stand on one line. The placement is exact, so a tenth of a unit is left for rounding only —
// far inside the half pixel of SC-007, and tight enough to see the old glyph's 0.2 offset.
for (const [index, entity] of fixture.entities.entries()) {
  const start = svg.indexOf(`<g id="a_hd${index}">`);
  const headerCell = svg.slice(start, svg.indexOf(`<g id="a_fn${index}_`, start) > 0 ? svg.indexOf(`<g id="a_fn${index}_`, start) : start + 6000);
  const band = /<polygon[^>]* points="([^"]+)"/.exec(headerCell)?.[1] ?? "";
  const ys = band.trim().split(/\s+/).map((pair) => Number(pair.split(",")[1]));
  const bandMiddle = (Math.min(...ys) + Math.max(...ys)) / 2;
  const glyph = /class="erd-kind-icon"[^>]*translate\(([-\d.]+),([-\d.]+)\) scale\(([\d.]+)\)/.exec(headerCell);
  const glyphMiddle = glyph ? Number(glyph[2]) + (Number(glyph[3]) * 24) / 2 : NaN;
  const text = /<text[^>]* y="([-\d.]+)"[^>]* font-size="([\d.]+)"[^>]*>/.exec(headerCell.slice(headerCell.indexOf(`a_hn${index}`)));
  const nameMiddle = text ? Number(text[1]) - CAP_HALF_EM * Number(text[2]) : NaN;
  check(
    `029 FR-033 ${entity.label}: the kind icon and the name stand on the header's middle line`,
    Math.abs(glyphMiddle - nameMiddle) <= 0.1 && Math.abs(glyphMiddle - bandMiddle) <= 0.1,
    `icon ${glyphMiddle.toFixed(2)}, name ${nameMiddle.toFixed(2)}, band ${bandMiddle.toFixed(2)}`,
  );
}

// ── FR-111: frame and body ───────────────────────────────────────────────────
check(`029 FR-032 the outline is the mockup's: radius ${ERD_CARD_RADIUS}, ${ERD_CARD_STROKE} wide, in the domain colour`, frame !== null && Number(frame[6]) === ERD_CARD_RADIUS && Number(frame[1]) === ERD_CARD_STROKE, frame ? `rx ${frame[6]}, width ${frame[1]}` : "no outline");
const body = /<rect fill="white" stroke="none" x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="([\d.]+)"\/>/.exec(table);
check("FR-111 body is white, the card's own shape", body !== null && Number(body[1]) === frameLeft && Number(body[5]) === ERD_CARD_RADIUS);
const clipId = /<g id="a_hd0">[\s\S]*?<polygon clip-path="url\(#([^)]+)\)"/.exec(table)?.[1] ?? "";
const clip = new RegExp(`<clipPath id="${clipId}"><rect x="([-\\d.]+)" y="([-\\d.]+)" width="([\\d.]+)" height="([\\d.]+)" rx="([\\d.]+)"/></clipPath>`).exec(svg);
// The header is trimmed by the very rounded rectangle the outline draws, so both corners are one curve (SC-007).
check(
  "029 SC-007 the header's corners follow the outline's curve",
  clip !== null && frame !== null && clip.slice(1, 6).every((value, i) => Math.abs(Number(value) - Number([frame[2], frame[3], frame[4], frame[5], frame[6]][i])) < 0.5),
  clip ? `clip ${clip.slice(1).join(" ")}` : "no clip",
);
check("029 FR-032 every fill of the card is trimmed to it", [...table.matchAll(/<polygon\b[^>]*>/g)].every((m) => m[0].includes("clip-path=")), "a polygon is not clipped");
check("029 FR-032 Graphviz's own rounded outline is gone", !/<path fill="none" stroke="[^"]+" d="M[^"]*C/.test(table));

// ── FR-112: row tint ─────────────────────────────────────────────────────────
const rowFills = [0, 1, 2, 3].map((row) => /<polygon(?: clip-path="[^"]+")? fill="([^"]+)"( fill-opacity="([\d.]+)")?/.exec(cell(`fn0_${row}`)));
check("FR-112 rows 1 and 3 are white", rowFills[0]?.[1] === "#ffffff" && rowFills[2]?.[1] === "#ffffff");
check(
  "FR-112 rows 2 and 4 are tinted with the domain colour at 6 %",
  [rowFills[1], rowFills[3]].every((fill) => fill?.[1] === COLOUR && Math.abs(Number(fill[3]) - 0.06) < 0.005),
  rowFills.map((fill) => `${fill?.[1]} ${fill?.[3] ?? ""}`).join(" | "),
);
const rowPoints = /<polygon[^>]* points="([^"]+)"/.exec(cell("fn0_0"))?.[1] ?? "";
check(`FR-115 a row is about ${ERD_ROW_HEIGHT_PT} high`, Math.abs(heightOf(rowPoints) - ERD_ROW_HEIGHT_PT) < 1.5, `${heightOf(rowPoints)}`);

// ── FR-113: keys ─────────────────────────────────────────────────────────────
const pk = new RegExp(`<text[^>]* x="([-\\d.]+)"[^>]*font-weight="bold"[^>]*fill="${ERD_PK_COLOUR}">PK</text>`).exec(table);
const fk = new RegExp(`<text[^>]*font-weight="bold"[^>]*fill="${ERD_FK_COLOUR}">FK</text>`).test(table);
check("FR-113 PK is bold rust-red", pk !== null);
check("FR-113 FK is bold slate", fk);
const nameX = Number(/<text[^>]* x="([-\d.]+)"/.exec(cell("fn0_0"))?.[1]);
check("FR-113 PK sits in a column of its own, before the field name", pk !== null && Number(pk[1]) + 10 < nameX, `PK ${pk?.[1]}, name ${nameX}`);

// ── FR-114: name and type ────────────────────────────────────────────────────
const typeText = /<text[^>]* x="([-\d.]+)"[^>]*font-size="([\d.]+)"[^>]*fill="([^"]+)">str<\/text>/.exec(cell("ft0_0"));
const nameSize = Number(/font-size="([\d.]+)"/.exec(cell("fn0_0"))?.[1]);
check("FR-114 the type is smaller than the field name", typeText !== null && Number(typeText[2]) < nameSize, `${typeText?.[2]} < ${nameSize}`);
check("FR-114 the type is grey", typeText?.[3] === ERD_TYPE_COLOUR);
const typeCellRight = Math.max(...(/<polygon[^>]* points="([^"]+)"/.exec(cell("ft0_0"))?.[1] ?? "0,0").trim().split(/\s+/).map((pair) => Number(pair.split(",")[0])));
check("FR-114 the type is right-aligned, the name left", typeText !== null && typeCellRight - Number(typeText[1]) < 25 && nameX < Number(typeText[1]), `type ${typeText?.[1]} in …${typeCellRight}`);

// ── FR-115: lines ────────────────────────────────────────────────────────────
const edge = svg.slice(svg.indexOf('<g id="re0"'), svg.indexOf("</g>", svg.indexOf('<g id="re0"')));
check("FR-115 the line is grey", edge.includes('stroke="#94a3b8"'));
check("FR-115 a generalization is dashed", /<path[^>]*stroke-dasharray=/.test(edge));
// ERD notation has no arrows (spec 029, FR-043): a generalization ends in bars and a circle — two bars
// at the head, a bar and a circle at the variant — never a triangle. Graphviz closes each polygon by
// repeating its first point, so a triangle has 4 points and a bar 5.
const polygonPoints = [...edge.matchAll(/<polygon[^>]* points="([^"]+)"/g)].map((m) => m[1]!.trim().split(/\s+/).length);
check("FR-043 a generalization has no arrowhead", !polygonPoints.includes(4), `${polygonPoints}`);
check("FR-043 three bars: two at the head, one at the variant", polygonPoints.filter((n) => n === 5).length === 3, `${polygonPoints}`);
check("FR-043 one circle, at the variant", (edge.match(/<ellipse/g) ?? []).length === 1);

if (failures) {
  console.error(`${failures} assertion(s) failed`);
  process.exit(1);
}
console.log("all assertions passed");
