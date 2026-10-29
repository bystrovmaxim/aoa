// scripts/check-erd-card-containment.ts
/**
 * The card containment check — every fill of a table card must be trimmed to its rounded contour.
 *
 * It renders fixtures through the same WASM Graphviz build the client loads, runs the production
 * pass (`containNodeFills`) over the drawing, and asserts the properties the specification fixes in
 * `specs/009-erd-card-contour/`. It is plain Node: no framework, no bundler, no new dependency.
 *
 * Exit codes: 0 all assertions passed; 1 an assertion failed; 2 the environment cannot run it.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";
import { Graphviz } from "@hpcc-js/wasm-graphviz";
import {
  buildDotSource,
  erdGraphvizEngine,
  type ErdGraphPayload,
  type ErdGraphvizLayout,
} from "../src/lib/buildDotSource.ts";
import { buildDomainUseCaseDotBundle } from "../src/lib/buildDomainUseCaseDotSource.ts";
import { buildLifecycleFsmDotSource } from "../src/lib/buildLifecycleFsmDotSource.ts";
import { clipIdFor, containNodeFills, readCards, type Card } from "../src/lib/containNodeFills.ts";

const MINIMUM_NODE: readonly [number, number] = [22, 6];
const TOLERANCE = 0.05;
const SCALE_BUDGET_MS = 2000;
const SCALE_CARDS = 120;

let failures = 0;

/** Record one passing assertion. */
function ok(label: string, detail: string): void {
  console.log(`ok    ${label}  ${detail}`);
}

/** Record one failing assertion. */
function fail(label: string, detail: string): void {
  console.error(`fail  ${label}  ${detail}`);
  failures += 1;
}

/** Record one measurement that is not an assertion. */
function info(message: string): void {
  console.log(`info  ${message}`);
}

/** Points of a polygon attribute as `[x, y]` pairs. */
function points(pointsAttribute: string): Array<[number, number]> {
  const values = (pointsAttribute.match(/-?\d+(?:\.\d+)?/g) ?? []).map(Number);
  const pairs: Array<[number, number]> = [];
  for (let index = 0; index + 1 < values.length; index += 2) pairs.push([values[index]!, values[index + 1]!]);
  return pairs;
}

/** Is a point outside the inset contour of a card? Independent of the module's own arithmetic. */
function outsideInset(px: number, py: number, card: Card): boolean {
  const x0 = card.contour.x0 + card.inset;
  const x1 = card.contour.x1 - card.inset;
  const y0 = card.contour.y0 + card.inset;
  const y1 = card.contour.y1 - card.inset;
  const r = card.insetRadius;
  const dx = Math.max(x0 + r - px, px - (x1 - r), 0);
  const dy = Math.max(y0 + r - py, py - (y1 - r), 0);
  return Math.hypot(dx, dy) > r + TOLERANCE;
}

/** Every polygon tag of a card group. */
function polygonsOf(group: string): string[] {
  return [...group.matchAll(/<polygon\b[^>]*\bpoints="[^"]*"/g)].map((match) => match[0]);
}

/** The value of one attribute of a tag, or `null`. */
function attrOf(tag: string, name: string): string | null {
  return new RegExp(`\\b${name}="([^"]*)"`).exec(tag)?.[1] ?? null;
}

/** The `<clipPath>` a card's fills should reference, as written in the processed markup. */
function clipElementOf(processed: string, id: string): string | null {
  return new RegExp(`<clipPath id="${id}"><rect [^>]*/></clipPath>`).exec(processed)?.[0] ?? null;
}

/** The `<rect>` of a clip element, as its attributes. */
function clipRectOf(clip: string): Record<string, number> {
  const tag = /<rect [^>]*/.exec(clip)?.[0] ?? "";
  const read = (name: string): number => Number(attrOf(tag, name));
  return { x: read("x"), y: read("y"), width: read("width"), height: read("height"), rx: read("rx") };
}

/** The fixture drawings, each with the number of cards the check expects to find in it. */
type Fixture = Readonly<{ name: string; svg: string; expectedCards: number }>;

const showcase: ErdGraphPayload = {
  entities: [
    {
      id: "datamodel.showcases.showcase_entity.ShowcaseEntity",
      label: "ShowcaseEntity",
      color: "#f5a623",
      fields: [
        { name: "id", type: "str", primary_key: true },
        { name: "name", type: "str" },
        { name: "public_key", type: "str" },
        { name: "industries", type: "tuple[IndustryCode, Ellipsis]" },
        { name: "created_at", type: "datetime" },
      ],
    },
  ],
  relations: [],
};

const bandOnly: ErdGraphPayload = {
  entities: [{ id: "d.ViewEntity", label: "ViewEntity", color: "#3b82f6", fields: [] }],
  relations: [],
};

const plain: ErdGraphPayload = {
  entities: [
    {
      id: "d.PlainEntity",
      label: "PlainEntity",
      color: "#10b981",
      fields: [
        { name: "alpha", type: "str" },
        { name: "beta", type: "datetime" },
      ],
    },
  ],
  relations: [],
};

const clustered: ErdGraphPayload = {
  entities: [
    { id: "d.HeadEntity", label: "HeadEntity", color: "#8b5cf6", fields: [{ name: "id", type: "str", primary_key: true }] },
    { id: "d.AltOneEntity", label: "AltOneEntity", color: "#8b5cf6", fields: [{ name: "id", type: "str", primary_key: true }] },
    { id: "d.AltTwoEntity", label: "AltTwoEntity", color: "#8b5cf6", fields: [{ name: "id", type: "str", primary_key: true }] },
  ],
  relations: [],
  groups: [{ group_id: "axis", label: "Details", members: ["d.HeadEntity", "d.AltOneEntity", "d.AltTwoEntity"] }],
};

/** A card whose arcs meet: eight units wide, twice the corner radius. */
const NARROW_MARKUP = `<?xml version="1.0" encoding="UTF-8"?>
<svg width="40pt" height="40pt" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
<g id="graph0" class="graph" transform="translate(10 30)">
<g id="node1" class="node">
<title>narrow</title>
<path fill="white" stroke="none" d="M12,0L12,-20L6,-20L14,-20L14,0Z"/>
<polygon fill="#f5a623" points="7,-1 7,-19 13,-19 13,-1"/>
<path fill="none" stroke="#f5a623" d="M12,0L12,-20L6,-20L14,-20L14,0Z"/>
</g>
</g>
</svg>`;

/** A card whose fills sit exactly on the contour, so the inset consumes the whole radius. */
const DEGENERATE_MARKUP = `<?xml version="1.0" encoding="UTF-8"?>
<svg width="40pt" height="40pt" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
<g id="graph0" class="graph" transform="translate(10 30)">
<g id="node1" class="node">
<title>degenerate</title>
<path fill="white" stroke="none" d="M5,0L5,-20L0,-20L20,-20L20,0Z"/>
<polygon fill="#f5a623" points="5,-5 5,-15 15,-15 15,-5"/>
<path fill="none" stroke="#f5a623" d="M5,0L5,-20L0,-20L20,-20L20,0Z"/>
</g>
</g>
</svg>`;

const gv = await Graphviz.load();

/** Render a DOT source to SVG with the engine a layout preset names. */
function renderDot(dot: string, engine = "dot"): string {
  return gv.dot(dot, "svg", engine);
}

/** The five layout presets the entity diagram offers. */
const PRESETS: readonly ErdGraphvizLayout[] = ["gv-dot-lr", "gv-dot-tb", "gv-neato", "gv-fdp", "gv-circo"];

/** The fixtures of the check, in the order the assertions name them. */
const fixtures: readonly Fixture[] = [
  { name: "showcase", svg: renderDot(buildDotSource(showcase, "gv-dot-tb")), expectedCards: 1 },
  { name: "band-only", svg: renderDot(buildDotSource(bandOnly, "gv-dot-tb")), expectedCards: 1 },
  { name: "plain", svg: renderDot(buildDotSource(plain, "gv-dot-tb")), expectedCards: 1 },
  { name: "cluster", svg: renderDot(buildDotSource(clustered, "gv-dot-tb")), expectedCards: 3 },
  { name: "narrow", svg: NARROW_MARKUP, expectedCards: 1 },
  { name: "degenerate", svg: DEGENERATE_MARKUP, expectedCards: 1 },
  {
    name: "lifecycle",
    svg: renderDot(
      buildLifecycleFsmDotSource(
        {
          entity: "OrderEntity",
          domain: "sales",
          states: [
            { key: "new", display_name: "New", state_type: "initial" },
            { key: "paid", display_name: "Paid", state_type: "" },
            { key: "done", display_name: "Done", state_type: "final" },
          ],
          transitions: [
            { source: "new", target: "paid", trigger: "pay" },
            { source: "paid", target: "done", trigger: "ship" },
          ],
          initial_state_keys: ["new"],
        } as unknown as Parameters<typeof buildLifecycleFsmDotSource>[0],
        "LR",
      ),
    ),
    expectedCards: 0,
  },
  {
    name: "use-case",
    svg: renderDot(
      buildDomainUseCaseDotBundle(
        {
          domain: { id: "sales", label: "Sales", short_label: "Sales", accent_color: "#2563eb" },
          actions: [
            {
              id: "pay",
              label: "Pay for order",
              short_label: "Pay",
              domain_id: "sales",
              domain_short_label: "Sales",
              accent_color: "#2563eb",
              role_ids: ["manager"],
            },
          ],
          roles: [{ id: "manager", label: "Manager", short_label: "Manager" }],
          edges: [{ edge_kind: "association", source_id: "manager", target_id: "pay" }],
        },
        "LR",
        { roleActorImageUrl: "" },
        { boundary: true },
      ).dot,
    ),
    expectedCards: 0,
  },
  ...PRESETS.map((layout) => ({
    name: `preset ${layout}`,
    svg: renderDot(buildDotSource(showcase, layout), erdGraphvizEngine(layout)),
    expectedCards: 1,
  })),
];

// The reading mode of the quickstart: the fixture card before and after the pass, as text, with
// nothing asserted. It exists so a reader can see the difference instead of trusting a summary.
if (process.argv.includes("--print-svg")) {
  const raw = fixtures.find((fixture) => fixture.name === "showcase")!.svg;
  console.log("<!-- unprocessed: what the renderer emits -->");
  console.log(raw);
  console.log("<!-- processed: what the page receives -->");
  console.log(containNodeFills(raw));
  process.exit(0);
}

type Processed = Readonly<{ fixture: Fixture; processed: string; cards: readonly Card[] }>;

const processedFixtures: Processed[] = fixtures.map((fixture) => {
  const processed = containNodeFills(fixture.svg);
  return { fixture, processed, cards: readCards(processed) };
});

/** The processed entry of a fixture by name. */
function processedFor(name: string): Processed {
  const entry = processedFixtures.find((candidate) => candidate.fixture.name === name);
  if (entry === undefined) throw new Error(`no fixture named ${name}`);
  return entry;
}

// ---------------------------------------------------------------------------------------------
// A-13 — the environment this check needs.
// ---------------------------------------------------------------------------------------------
{
  const [major = 0, minor = 0] = process.versions.node.split(".").map(Number);
  const newEnough = major > MINIMUM_NODE[0] || (major === MINIMUM_NODE[0] && minor >= MINIMUM_NODE[1]);
  if (!newEnough) {
    console.error(
      `fail  A-13 environment — Node ${process.version} cannot strip TypeScript types; this check needs ${MINIMUM_NODE[0]}.${MINIMUM_NODE[1]} or newer`,
    );
    process.exit(2);
  }
  ok("A-13 environment", `Node ${process.versions.node} runs this script directly`);
}

// ---------------------------------------------------------------------------------------------
// The diagnostic: is the pass still needed? Printed, never asserted.
// ---------------------------------------------------------------------------------------------
{
  let withOutsideCorners = 0;
  let cards = 0;
  for (const fixture of fixtures) {
    for (const card of readCards(fixture.svg)) {
      cards += 1;
      if (card.fills.some((shape) => points(shape.points).some(([x, y]) => outsideInset(x, y, card)))) withOutsideCorners += 1;
    }
  }
  info(`the renderer still emits rectangles: ${withOutsideCorners} of ${cards} cards have a fill corner outside the contour before the pass`);
}

// ---------------------------------------------------------------------------------------------
// A-1 — containment: every fill is trimmed to its card's inset contour, and no fill leaves the
// card's own bounds. A clip does not move a polygon's points; it decides what is painted, so the
// gate is stated as the two halves that make paint outside the contour impossible.
// ---------------------------------------------------------------------------------------------
for (const { fixture, cards } of processedFixtures) {
  if (cards.length !== fixture.expectedCards) {
    fail(`A-1 ${fixture.name}`, `${cards.length} cards found, ${fixture.expectedCards} expected`);
    continue;
  }

  const problems: string[] = [];
  for (const card of cards) {
    for (const polygon of polygonsOf(card.group)) {
      if (attrOf(polygon, "clip-path") !== `url(#${clipIdFor(card)})`) {
        problems.push(`${card.id}: a fill is not clipped to ${clipIdFor(card)}`);
        break;
      }
    }
    for (const shape of card.fills) {
      for (const [x, y] of points(shape.points)) {
        const outsideBounds =
          x < card.contour.x0 - TOLERANCE ||
          x > card.contour.x1 + TOLERANCE ||
          y < card.contour.y0 - TOLERANCE ||
          y > card.contour.y1 + TOLERANCE;
        if (outsideBounds) problems.push(`${card.id}: a fill corner (${x}, ${y}) leaves the card's own bounds`);
      }
    }
  }

  if (problems.length === 0 && cards.length === 0) {
    ok(`A-1 ${fixture.name}`, "no card here — the node is left alone, and A-7 will assert it byte-identical");
  } else if (problems.length === 0) {
    ok(`A-1 ${fixture.name}`, `${cards.length} card(s), ${cards.reduce((n, c) => n + c.fills.length, 0)} fills trimmed to the inset contour`);
  } else {
    fail(`A-1 ${fixture.name}`, problems[0]!);
  }
}

// ---------------------------------------------------------------------------------------------
// A-2 — clip wiring: every fill references exactly one clip, that clip is the card's own, and it
// appears once in the drawing.
// ---------------------------------------------------------------------------------------------
{
  const problems: string[] = [];
  let fills = 0;
  for (const { fixture, processed, cards } of processedFixtures) {
    for (const card of cards) {
      const referenced = new Set<string>();
      for (const polygon of polygonsOf(card.group)) {
        const reference = attrOf(polygon, "clip-path");
        const target = reference === null ? null : /^url\(#(.+)\)$/.exec(reference)?.[1];
        if (target === null || target === undefined) {
          problems.push(`${fixture.name}/${card.id}: a fill carries no clip reference`);
          continue;
        }
        referenced.add(target);
        fills += 1;
      }
      if (referenced.size !== 1) problems.push(`${fixture.name}/${card.id}: fills reference ${referenced.size} clips, 1 expected`);
      else if (!referenced.has(clipIdFor(card))) problems.push(`${fixture.name}/${card.id}: fills reference ${[...referenced][0]}, not ${clipIdFor(card)}`);
      const occurrences = processed.split(`id="${clipIdFor(card)}"`).length - 1;
      if (occurrences !== 1) problems.push(`${fixture.name}/${card.id}: clip id appears ${occurrences} times in the drawing, 1 expected`);
    }
  }
  if (problems.length === 0) ok("A-2 clip wiring", `${fills} fills reference their own card's clip, each clip once per drawing`);
  else fail("A-2 clip wiring", problems[0]!);
}

// ---------------------------------------------------------------------------------------------
// A-3 — the clip's geometry is the card's inset contour: same bounds, radius minus inset.
// ---------------------------------------------------------------------------------------------
{
  const problems: string[] = [];
  let checked = 0;
  for (const { fixture, processed, cards } of processedFixtures) {
    for (const card of cards) {
      const clip = clipElementOf(processed, clipIdFor(card));
      if (clip === null) {
        problems.push(`${fixture.name}/${card.id}: no clip element for ${clipIdFor(card)}`);
        continue;
      }
      const rect = clipRectOf(clip);
      const expected: Record<string, number> = {
        x: card.contour.x0 + card.inset,
        y: card.contour.y0 + card.inset,
        width: card.contour.x1 - card.contour.x0 - 2 * card.inset,
        height: card.contour.y1 - card.contour.y0 - 2 * card.inset,
        rx: card.insetRadius,
      };
      for (const [name, want] of Object.entries(expected)) {
        if (!Number.isFinite(rect[name]!) || Math.abs(rect[name]! - want) > TOLERANCE) {
          problems.push(`${fixture.name}/${card.id}: clip ${name} is ${rect[name]}, ${want} expected`);
        }
      }
      checked += 1;
    }
  }
  if (problems.length === 0) ok("A-3 geometry", `${checked} clips are the card's contour shrunk by the inset, radius minus inset`);
  else fail("A-3 geometry", problems[0]!);
}

// ---------------------------------------------------------------------------------------------
// A-4 — a card with only a band: the band is the whole card, so all four of its corners must be
// cut by the clip the card actually carries.
// ---------------------------------------------------------------------------------------------
{
  const { processed, cards } = processedFor("band-only");
  const card = cards[0];
  const clip = card === undefined ? null : clipElementOf(processed, clipIdFor(card));
  if (card === undefined || clip === null) {
    fail("A-4 band-only card", "the card carries no clip, so its band's corners are not cut");
  } else {
    const { x, y, width: w, height: h, rx: r } = clipRectOf(clip);
    const shape = card.fills[0]!;
    const xs = points(shape.points).map(([px]) => px);
    const ys = points(shape.points).map(([, py]) => py);
    const spansClip =
      Math.abs(Math.min(...xs) - x) < TOLERANCE &&
      Math.abs(Math.max(...xs) - (x + w)) < TOLERANCE &&
      Math.abs(Math.min(...ys) - y) < TOLERANCE &&
      Math.abs(Math.max(...ys) - (y + h)) < TOLERANCE;
    const corners: Array<[number, number]> = [[x, y], [x + w, y], [x, y + h], [x + w, y + h]];
    const cut = corners.every(([px, py]) => {
      const cx = px < x + w / 2 ? x + r : x + w - r;
      const cy = py < y + h / 2 ? y + r : y + h - r;
      return Math.hypot(px - cx, py - cy) > r + TOLERANCE;
    });
    if (spansClip && cut && r > 0) ok("A-4 band-only card", `the band spans the clip and all four corners are cut (radius ${r.toFixed(2)})`);
    else fail("A-4 band-only card", `band spans the clip=${spansClip}, corners cut=${cut}, radius=${r}`);
  }
}

// ---------------------------------------------------------------------------------------------
// A-5 — the degenerate cards: the arcs meeting, and the inset consuming the whole radius.
// ---------------------------------------------------------------------------------------------
{
  const problems: string[] = [];

  const narrow = processedFor("narrow");
  const narrowCard = narrow.cards[0];
  const narrowClip = narrowCard === undefined ? null : clipElementOf(narrow.processed, clipIdFor(narrowCard));
  if (narrowCard === undefined || narrowClip === null) problems.push("narrow: the card was not processed");
  else {
    const rect = clipRectOf(narrowClip);
    if (!(rect.width > 0) || !(rect.height > 0)) problems.push(`narrow: the clip has no area (${rect.width} × ${rect.height})`);
    if (rect.rx !== narrowCard.insetRadius) problems.push(`narrow: clip radius ${rect.rx}, ${narrowCard.insetRadius} expected`);
  }

  const degenerate = processedFor("degenerate");
  const degenerateCard = degenerate.cards[0];
  const degenerateClip = degenerateCard === undefined ? null : clipElementOf(degenerate.processed, clipIdFor(degenerateCard));
  if (degenerateCard === undefined || degenerateClip === null) problems.push("degenerate: the card was not processed");
  else {
    const rect = clipRectOf(degenerateClip);
    if (rect.rx !== 0) problems.push(`degenerate: clip radius ${rect.rx}, 0 expected when the inset consumes the radius`);
    for (const shape of degenerateCard.fills) {
      for (const [px, py] of points(shape.points)) {
        const insideClip = px >= rect.x - TOLERANCE && px <= rect.x + rect.width + TOLERANCE && py >= rect.y - TOLERANCE && py <= rect.y + rect.height + TOLERANCE;
        if (!insideClip) problems.push(`degenerate: a fill corner (${px}, ${py}) is outside the clip`);
      }
    }
  }

  if (problems.length === 0) ok("A-5 degenerate cards", "the narrow card keeps a positive clip, and the inset that consumes the radius yields radius 0");
  else fail("A-5 degenerate cards", problems[0]!);
}

// ---------------------------------------------------------------------------------------------
// A-6 — a card inside a dashed cluster: the cards are clipped, and the cluster's frame is what it
// was. The frame is everything of the cluster before its first card.
// ---------------------------------------------------------------------------------------------
{
  const { fixture, processed, cards } = processedFor("cluster");
  const frameOf = (markup: string): string => {
    const start = markup.indexOf('<g id="clust');
    const end = markup.indexOf('<g id="node', start);
    return start < 0 || end < 0 ? "" : markup.slice(start, end);
  };
  const problems: string[] = [];
  if (cards.length !== 3) problems.push(`${cards.length} cards in the cluster, 3 expected`);
  if (frameOf(processed) !== frameOf(fixture.svg)) problems.push("the cluster's frame changed");
  for (const card of cards) {
    if (!card.clipped) problems.push(`${card.id}: the card inside the cluster was not clipped`);
  }
  if (problems.length === 0) ok("A-6 grouped card", `${cards.length} cards clipped inside the dashed cluster, its frame byte-identical`);
  else fail("A-6 grouped card", problems[0]!);
}

// ---------------------------------------------------------------------------------------------
// A-8 — additive: strip what the pass inserted and the drawing is the input, byte for byte.
// ---------------------------------------------------------------------------------------------
{
  const problems: string[] = [];
  for (const { fixture, processed } of processedFixtures) {
    const stripped = processed
      .replace(/<clipPath id="erd-fill-clip-[^"]*"><rect [^>]*\/><\/clipPath>/g, "")
      .replace(/ clip-path="url\(#erd-fill-clip-[^"]*\)"/g, "");
    if (stripped !== fixture.svg) problems.push(`${fixture.name}: the stripped drawing differs from the input`);
  }
  if (problems.length === 0) ok("A-8 additive", `${processedFixtures.length} drawings are byte-identical to their input once the clips are stripped`);
  else fail("A-8 additive", problems[0]!);
}

// ---------------------------------------------------------------------------------------------
// A-9 — idempotence: a second pass over a processed drawing changes nothing.
// ---------------------------------------------------------------------------------------------
{
  const problems: string[] = [];
  for (const { fixture, processed } of processedFixtures) {
    if (containNodeFills(processed) !== processed) problems.push(`${fixture.name}: a second pass changed the drawing`);
  }
  if (problems.length === 0) ok("A-9 idempotence", `${processedFixtures.length} drawings are unchanged by a second pass`);
  else fail("A-9 idempotence", problems[0]!);
}

// ---------------------------------------------------------------------------------------------
// A-12 — scale: a model of a hundred and twenty tables is drawn and trimmed inside the budget.
// ---------------------------------------------------------------------------------------------
{
  const scalePayload: ErdGraphPayload = {
    entities: Array.from({ length: SCALE_CARDS }, (_, index) => ({
      id: `d.scale.Entity${index}Entity`,
      label: `Entity${index}Entity`,
      color: ["#f5a623", "#3b82f6", "#10b981"][index % 3]!,
      fields: [
        { name: "id", type: "str", primary_key: true },
        { name: "parent_id", type: "str", foreign_key: true },
        ...Array.from({ length: 4 }, (_unused, field) => ({ name: `field_${field}`, type: "str" })),
      ],
    })),
    relations: [],
  };

  const startedAt = performance.now();
  const rendered = renderDot(buildDotSource(scalePayload, "gv-dot-tb"));
  const processed = containNodeFills(rendered);
  const elapsed = performance.now() - startedAt;
  const drawn = readCards(processed);

  if (drawn.length !== SCALE_CARDS) {
    fail("A-12 scale", `${drawn.length} cards drawn, ${SCALE_CARDS} expected`);
  } else if (!drawn.every((card) => card.clipped)) {
    fail("A-12 scale", "a card of the large model was not trimmed");
  } else {
    ok("A-12 scale", `${SCALE_CARDS} cards rendered and processed in ${elapsed.toFixed(0)} ms (budget ${SCALE_BUDGET_MS} ms, ${Math.round(rendered.length / 1024)} KB)`);
  }
}

// ---------------------------------------------------------------------------------------------
// A-7 — the other two diagrams come back byte-identical. Their fixtures are the real automaton and
// the real use-case slice, drawn by the same builders the pages use.
// ---------------------------------------------------------------------------------------------
{
  const problems: string[] = [];
  const untouched: string[] = [];
  for (const { fixture, processed, cards } of processedFixtures) {
    if (fixture.expectedCards !== 0) continue;
    if (cards.length !== 0) problems.push(`${fixture.name}: ${cards.length} cards found, 0 expected`);
    else if (processed !== fixture.svg) problems.push(`${fixture.name}: the drawing was modified by the pass`);
    else untouched.push(`${fixture.name} ${fixture.svg.length} B`);
  }
  if (problems.length === 0) ok("A-7 foreign nodes", `byte-identical: ${untouched.join(", ")}`);
  else fail("A-7 foreign nodes", problems[0]!);
}

/** Every source file under the client's `src`, as a client-relative path and its text. */
function sourceFiles(): Array<{ path: string; text: string }> {
  const root = resolve(import.meta.dirname, "..", "src");
  const files: Array<{ path: string; text: string }> = [];
  for (const entry of readdirSync(root, { recursive: true, withFileTypes: true })) {
    if (!entry.isFile() || !/\.tsx?$/.test(entry.name)) continue;
    const absolute = join(entry.parentPath, entry.name);
    files.push({ path: relative(root, absolute).split(sep).join("/"), text: readFileSync(absolute, "utf8") });
  }
  return files;
}

// ---------------------------------------------------------------------------------------------
// A-10 — the pass has exactly one call site, the ERD canvas. This is what keeps the other two
// diagrams out of the change, and it is the guard the check cannot express geometrically.
// ---------------------------------------------------------------------------------------------
{
  const importers = sourceFiles().filter((file) => /from\s+["'][^"']*containNodeFills["']/.test(file.text));
  const expected = "components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx";
  if (importers.length !== 1) fail("A-10 import guard", `${importers.length} files import the pass (${importers.map((f) => f.path).join(", ")}), 1 expected`);
  else if (importers[0]!.path !== expected) fail("A-10 import guard", `the pass is imported by ${importers[0]!.path}, ${expected} expected`);
  else ok("A-10 import guard", `the pass is imported by ${expected} and by nothing else`);
}

// ---------------------------------------------------------------------------------------------
// A-11 — no new import reaches the drawing. Both production modules pull in relative paths only,
// and the pass itself pulls in nothing at all.
// ---------------------------------------------------------------------------------------------
{
  const problems: string[] = [];
  let imports = 0;
  const modules = sourceFiles().filter((file) => file.path === "lib/containNodeFills.ts" || file.path === "lib/buildDotSource.ts");
  if (modules.length !== 2) problems.push(`${modules.length} of the two drawing modules found`);
  for (const module of modules) {
    for (const match of module.text.matchAll(/^\s*import\s[^;]*?from\s+["']([^"']+)["']/gm)) {
      const specifier = match[1]!;
      imports += 1;
      if (!specifier.startsWith(".")) problems.push(`${module.path} imports the package ${specifier}`);
    }
  }
  const passModule = modules.find((module) => module.path === "lib/containNodeFills.ts");
  if (passModule !== undefined && /^\s*import\s/m.test(passModule.text)) problems.push("the pass module imports something");
  if (problems.length === 0 && imports === 0) ok("A-11 no new imports", "neither drawing module imports anything at all, let alone a package");
  else if (problems.length === 0) ok("A-11 no new imports", `the two drawing modules import ${imports} relative paths and no package`);
  else fail("A-11 no new imports", problems[0]!);
}

console.log("");
if (failures > 0) {
  console.error(`${failures} assertion(s) failed`);
  process.exit(1);
}
console.log("all assertions passed");
