// scripts/check-erd-kinds-and-lines.ts
/**
 * The ERD drawing check of spec 027 — what a table and a line look like in the SVG the page shows.
 *
 * It renders fixtures through the same WASM Graphviz build the client loads, runs the production
 * passes (`containNodeFills`, `placeKindIcons`) over the drawing, and asserts the specification's
 * visible rules: the minimum table width, the header's rounded fill, the kind icon before the name,
 * addressable cells, a type column without "→ …" or "FK -> " and on the right edge, and see-through
 * specialization containers with a wider outline. It is plain Node: no framework, no bundler.
 *
 * Exit codes: 0 all assertions passed; 1 an assertion failed; 2 the environment cannot run it.
 */

import { Graphviz } from "@hpcc-js/wasm-graphviz";
import { buildDotSource, ERD_CARD_RADIUS, ERD_CARD_STROKE, ERD_TABLE_MIN_WIDTH_PT, type ErdGraphPayload } from "../src/lib/buildDotSource.ts";
import { containNodeFills } from "../src/lib/containNodeFills.ts";
import { drawErdCards, HEADER_INSET_PT, placeKindIcons } from "../src/lib/erdPostPass.ts";
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

/** Node widths and heights in points, by node name. */
function nodeSizes(dot: string): Map<string, { width: number; height: number }> {
  const json = JSON.parse(gv.layout(dot, "json", "dot")) as { objects?: Array<{ name: string; width: string; height: string }> };
  return new Map(
    (json.objects ?? [])
      .filter((o) => o.width !== undefined)
      .map((o) => [o.name, { width: Number.parseFloat(o.width) * 72, height: Number.parseFloat(o.height) * 72 }]),
  );
}

/** The x-extent of the polygon inside ``<g id="a_<id>">``. */
function boxOf(markup: string, id: string): { left: number; right: number } {
  const start = markup.indexOf(`<g id="a_${id}">`);
  const points = /points="([^"]+)"/.exec(markup.slice(start, markup.indexOf("</g>", start)))?.[1] ?? "";
  const xs = points.trim().split(/\s+/).map((p) => Number(p.split(",")[0]));
  return { left: Math.min(...xs), right: Math.max(...xs) };
}

/** The x of the first text inside ``<g id="a_<id>">``. */
function textXOf(markup: string, id: string): number {
  return Number(/<text[^>]* x="([-\d.]+)"/.exec(markup.slice(markup.indexOf(`<g id="a_${id}">`)))?.[1]);
}

/** The drawing the page shows for a payload: Graphviz, then the production passes. */
function drawn(data: ErdGraphPayload): string {
  return placeKindIcons(drawErdCards(containNodeFills(gv.layout(buildDotSource(data, "gv-dot-lr"), "svg", "dot")), ERD_CARD_RADIUS, ERD_CARD_STROKE), data.entities, kindGlyphSvg);
}

const field = (name: string, type: string, extra: Record<string, unknown> = {}) => ({ name, type, primary_key: false, foreign_key: false, ...extra });
// A type long even as a clean name (spec 029 shows `X | None`, cut to the column), so the table stays wide.
const longType = "Union[AssociationOne[BillingChargebackIngestCorrelateCoreEntity], NoneType]";

const fixture: ErdGraphPayload = {
  entities: [
    // A two-row dictionary: a stub today (122.4 pt).
    { id: "shop.GenderEnumEntity", label: "GenderEnumEntity", color: "#10b981", entity_kind: "enum", entity_kind_label: "Enumeration", fields: [{ ...field("id", "str"), primary_key: true }, field("is_obsolete", "bool")] },
    // A table wider than the minimum on its own.
    { id: "shop.PlayerCoreEntity", label: "PlayerCoreEntity", color: "#10b981", entity_kind: "core", entity_kind_label: "Core", fields: [{ ...field("id", "str"), primary_key: true }, field("gender", longType, { reference_qualname: "shop.GenderEnumEntity" }), { ...field("showcase", "ShowcaseCoreEntity"), foreign_key: true }] },
    // A kind Maxitor does not know, and a row without a kind.
    { id: "shop.OrderAggregateEntity", label: "OrderAggregateEntity", color: "#3b82f6", entity_kind: "aggregate", entity_kind_label: "Aggregate", fields: [{ ...field("id", "str"), primary_key: true }] },
    { id: "shop.LegacyEntity", label: "LegacyEntity", color: "#3b82f6", fields: [{ ...field("id", "str"), primary_key: true }] },
    // A specialization container with two members.
    { id: "shop.CardSpecEntity", label: "CardSpecEntity", color: "#3b82f6", entity_kind: "spec", fields: [{ ...field("id", "str"), primary_key: true }] },
    { id: "shop.BankSpecEntity", label: "BankSpecEntity", color: "#3b82f6", entity_kind: "spec", fields: [{ ...field("id", "str"), primary_key: true }] },
  ],
  relations: [{ source: "shop.PlayerCoreEntity", target: "shop.GenderEnumEntity", label: "gender", relationship_kind: "reference" }],
  groups: [{ group_id: "shop.PaymentCoreEntity:kind", label: "kind (by PaymentKindEnumEntity)", members: ["shop.CardSpecEntity", "shop.BankSpecEntity"] }],
};

// ── Minimum width ────────────────────────────────────────────────────────────
const dot = buildDotSource(fixture, "gv-dot-lr");
const withMinimum = nodeSizes(dot);
const natural = nodeSizes(dot.replaceAll(` WIDTH="${ERD_TABLE_MIN_WIDTH_PT}"`, ""));
const floor = ERD_TABLE_MIN_WIDTH_PT + 2;
for (const entity of fixture.entities) {
  const now = withMinimum.get(entity.id)!;
  const before = natural.get(entity.id)!;
  const expected = Math.max(before.width, floor);
  check(`width ${entity.label} ≥ ${floor} pt and never narrower than its content`, Math.abs(now.width - expected) < 0.6, `${before.width.toFixed(1)} → ${now.width.toFixed(1)} pt`);
  check(`height ${entity.label} unchanged by the minimum`, Math.abs(now.height - before.height) < 0.6, `${before.height.toFixed(1)} → ${now.height.toFixed(1)} pt`);
}
check("GenderEnumEntity was a stub before the minimum", natural.get("shop.GenderEnumEntity")!.width < floor - 50);
check("PlayerCoreEntity is wider than the minimum on its own", natural.get("shop.PlayerCoreEntity")!.width > floor + 10);

// ── Header, icon and cells ───────────────────────────────────────────────────
const svg = drawn(fixture);
// The same drawing before the icon pass: the name's width is read where Graphviz put it.
const raw = containNodeFills(gv.layout(dot, "svg", "dot"));
fixture.entities.forEach((entity, table) => {
  const group = svg.slice(svg.indexOf(`<title>${entity.id}</title>`), svg.indexOf("</g>\n<!--", svg.indexOf(`<title>${entity.id}</title>`)));
  const headerFill = new RegExp(`<polygon clip-path="url\\(#[^"]+\\)" fill="${entity.color}"`).test(group);
  check(`header of ${entity.label} is one fill trimmed to the rounded contour`, headerFill);
  for (const id of [`ks${table}`, `hn${table}`, `fn${table}_0`, `ft${table}_0`]) {
    check(`cell ${id} of ${entity.label} is addressable`, svg.includes(`<g id="a_${id}">`));
  }
  const slot = svg.slice(svg.indexOf(`<g id="a_ks${table}">`), svg.indexOf("</g>", svg.indexOf(`<g id="a_ks${table}">`)));
  check(`kind icon of ${entity.label} is drawn in its slot, white`, slot.includes('class="erd-kind-icon"') && slot.includes("#ffffff"));
  const iconX = Number(/class="erd-kind-icon"[^>]*translate\(([-\d.]+),/.exec(slot)?.[1]);
  const nameX = textXOf(svg, `hn${table}`);
  check(`kind icon of ${entity.label} sits right before the name`, Math.abs(nameX - (iconX + 13) - 4) < 0.6, `icon ${iconX}, name ${nameX}`);
  // Icon, gap and name sit at the left of the header, after the inset (spec 028, FR-110).
  const cell = boxOf(raw, `hn${table}`);
  const nameWidth = cell.left + cell.right - 2 * textXOf(raw, `hn${table}`);
  const header = boxOf(svg, `hd${table}`);
  check(`icon and name of ${entity.label} start at the left of the header`, Math.abs(iconX - (header.left + HEADER_INSET_PT)) < 0.6, `icon ${iconX.toFixed(1)}, header ${header.left}`);
  check(`icon and name of ${entity.label} stay inside the header`, iconX > header.left && nameX + nameWidth < header.right, `${iconX.toFixed(1)}–${(nameX + nameWidth).toFixed(1)} in ${header.left}–${header.right}`);
});
check("a kind Maxitor does not know is drawn as a monogram", /<g id="a_ks2">[\s\S]*?>ag<\/text>/.test(svg));
check("a row without a kind gets the unknown pictogram and its tooltip", svg.includes('<g id="a_ks3"><a xlink:title="Unknown">'));
check("the spec pictogram is drawn at 80 %", /<g id="a_ks4">[\s\S]*?scale\(0\.8\)/.test(svg));

// ── Type column ──────────────────────────────────────────────────────────────
const typeTexts = [...svg.matchAll(/<g id="a_ft\d+_\d+">[\s\S]*?<text[^>]*>([^<]*)<\/text>/g)].map((m) => m[1]!);
check("no type cell carries a → suffix", typeTexts.every((t) => !t.includes("→")) && !svg.includes("→"));
check("no type cell carries an FK -> prefix", typeTexts.every((t) => !t.startsWith("FK -&gt; ") && !t.startsWith("FK -> ")));
// Graphviz places right-aligned text by its x, not by text-anchor: compare with the same table left-aligned.
const typeX = (markup: string) => [...markup.matchAll(/<g id="a_ft0_(\d+)">[\s\S]*?<text[^>]* x="([-\d.]+)"/g)].map((m) => Number(m[2]));
const gender = { ...fixture, entities: [fixture.entities[0]!], relations: [], groups: [] };
const rightX = typeX(gv.layout(buildDotSource(gender, "gv-dot-lr"), "svg", "dot"));
const leftX = typeX(gv.layout(buildDotSource(gender, "gv-dot-lr").replaceAll('ALIGN="RIGHT"', 'ALIGN="LEFT"'), "svg", "dot"));
check("type cells are aligned to the right edge", rightX.length > 0 && rightX.every((x, i) => x > leftX[i]! + 20), `right ${rightX.join(",")} / left ${leftX.join(",")}`);

// ── Specialization container ─────────────────────────────────────────────────
const cluster = svg.slice(svg.indexOf('<g id="clust1"'), svg.indexOf("</g>", svg.indexOf('<g id="clust1"')));
check("the container is see-through and half a tone darker", /fill="#0f172a" fill-opacity="0\.05\d*"/.test(cluster), cluster.slice(0, 160));
check("the container outline is one point wider", cluster.includes('stroke-width="2"'));

// ── Lines: one per association, read the ERD way ───────────────────────────
const lines: ErdGraphPayload = {
  entities: [
    { id: "shop.PlayerCoreEntity", label: "PlayerCoreEntity", entity_kind: "core", fields: [{ ...field("id", "str"), primary_key: true }, { ...field("showcase", "ShowcaseCoreEntity"), foreign_key: true }] },
    { id: "shop.ShowcaseCoreEntity", label: "ShowcaseCoreEntity", entity_kind: "core", fields: [{ ...field("id", "str"), primary_key: true }, { ...field("players", "PlayerCoreEntity"), foreign_key: true }] },
    { id: "shop.RequestCoreEntity", label: "RequestCoreEntity", entity_kind: "core", fields: [{ ...field("id", "str"), primary_key: true }] },
    { id: "shop.ItemDetailEntity", label: "ItemDetailEntity", entity_kind: "detail", fields: [{ ...field("id", "str"), primary_key: true }] },
  ],
  relations: [
    // As the server sends them: a field paired with its inverse, and a pair with a second association.
    { source: "shop.PlayerCoreEntity", target: "shop.ShowcaseCoreEntity", label: "showcase (one)", relationship_kind: "association",
      source_cardinality: "zero_many", target_cardinality: "one", source_field: "showcase", target_field: "players" },
    { source: "shop.ItemDetailEntity", target: "shop.RequestCoreEntity", label: "offer_request (one)", relationship_kind: "association",
      source_cardinality: "zero_many", target_cardinality: "one", source_field: "offer_request", target_field: "offers" },
    { source: "shop.RequestCoreEntity", target: "shop.ItemDetailEntity", label: "chosen_offer (one)", relationship_kind: "association",
      source_cardinality: "zero_many", target_cardinality: "one", source_field: "chosen_offer", target_field: null },
    // Spec 029, FR-043: an optional relation (zero or one at the target), and a reference to a dictionary
    // (many referring rows, one value).
    { source: "shop.PlayerCoreEntity", target: "shop.RequestCoreEntity", label: "last_request", relationship_kind: "association",
      source_cardinality: "zero_many", target_cardinality: "zero_one", source_field: "last_request", target_field: null },
    { source: "shop.ItemDetailEntity", target: "shop.ShowcaseCoreEntity", label: "showcase", relationship_kind: "reference",
      source_cardinality: "zero_many", target_cardinality: "one", source_field: "showcase", target_field: null },
  ],
};
const lineSvg = gv.layout(buildDotSource(lines, "gv-dot-lr"), "svg", "dot");
/** The markup of the edge group Graphviz wrote for the ``k``-th relation. */
const edgeGroup = (k: number) => {
  const start = lineSvg.indexOf(`<g id="re${k}"`);
  return start < 0 ? "" : lineSvg.slice(start, lineSvg.indexOf("</g>\n<!--", start) > 0 ? lineSvg.indexOf("</g>\n<!--", start) : undefined);
};
const paired = edgeGroup(0);
check("a field and its inverse are one edge, addressable", paired !== "" && !lineSvg.includes('<g id="re0_'));
check("the edge carries both roles at its ends", />showcase<\/text>/.test(paired) && />players<\/text>/.test(paired));
check("the edge has no label in the middle", !paired.includes("showcase (one)"));
// Graphviz draws a tee as a bar polygon and a crow as a three-pronged polygon; both ends are drawn.
check("both ends are drawn", (paired.match(/<polygon /g) ?? []).length >= 2, `${(paired.match(/<polygon /g) ?? []).length} shapes`);
const dotLines = buildDotSource(lines, "gv-dot-lr");
check("the ends follow the cardinalities (crow's foot and ring at the many side, two bars at the one side)",
  dotLines.includes('[id="re0" dir=both arrowtail=crowodot arrowhead=teetee headlabel="showcase" taillabel="players" labelfontsize=9]'));
// Spec 029, FR-043: four distinct ends, each where its side is.
check("an optional end is a bar and a ring, a mandatory one two bars", /id="re3" dir=both arrowtail=crowodot arrowhead=teeodot/.test(dotLines));
check("a reference has its crow's foot at the referring table and one value at the dictionary", /id="re4" dir=both arrowtail=crowodot arrowhead=teetee/.test(dotLines));
check("every end of the drawing is one of the four crow's-foot ends", [...dotLines.matchAll(/arrow(?:tail|head)=(\w+)/g)].every((m) => ["teetee", "teeodot", "crowtee", "crowodot", "normal"].includes(m[1]!)));
check("a relation without an inverse has one role", dotLines.includes('headlabel="chosen_offer" labelfontsize=9]') && !/re2"[^\]]*taillabel/.test(dotLines));
const pathOf = (k: number) => /<path[^>]* d="([^"]+)"/.exec(edgeGroup(k))?.[1] ?? "";
check("two associations between the same tables are two distinct lines", pathOf(1) !== "" && pathOf(2) !== "" && pathOf(1) !== pathOf(2));

if (failures) {
  console.error(`${failures} assertion(s) failed`);
  process.exit(1);
}
console.log("all assertions passed");
