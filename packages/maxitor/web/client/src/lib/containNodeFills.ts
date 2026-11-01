// src/lib/containNodeFills.ts
/**
 * ERD card containment — brings every fill of a table card inside its rounded contour.
 *
 * Graphviz draws a table card as an HTML-like label: the outline is a rounded rectangle
 * (`STYLE="ROUNDED"` on the `<TABLE>`), while the header band and the row tints are plain
 * rectangles painted inside it. Their corners therefore stand outside the rounded corners of
 * the card. This module reads the shapes the renderer emitted, derives the card's contour and
 * the inset its fills keep from it, and — once the clipping step exists — trims every fill to
 * that inset contour.
 *
 * The work is done on the markup, not on the DOM, for one reason: the check that guards this
 * behaviour runs in plain Node and must exercise this very function, not a second implementation.
 *
 * Nothing here is a constant: the radius comes from the drawn path and the inset from the drawn
 * fills, so a renderer upgrade that changes either one changes the clipping with it.
 */

/** A card's rounded contour: the rectangle the outline spans and the radius of its corners. */
export type Contour = Readonly<{
  x0: number;
  x1: number;
  y0: number;
  y1: number;
  radius: number;
}>;

/** One coloured rectangle inside a card: the header band, a key tint or a body row. */
export type FillShape = Readonly<{
  fill: string;
  points: string;
}>;

/** A node group that qualifies as a card, with the geometry derived from its own drawing. */
export type Card = Readonly<{
  id: string;
  group: string;
  contour: Contour;
  fills: readonly FillShape[];
  inset: number;
  insetRadius: number;
  /** Whether the group already carries the clip this module inserts. */
  clipped: boolean;
}>;

const NODE_GROUP = /<g id="([^"]+)" class="node">([\s\S]*?)<\/g>/g;
const BACKDROP = /<path fill="white"[^>]*d="([^"]+)"/;
const FILL = /<polygon\b[^>]*\bfill="([^"]+)"[^>]*\bpoints="([^"]+)"/g;
const CLIP_ID_PREFIX = "erd-fill-clip-";

/** Numbers of a path or a polygon attribute, in their written order. */
function numbers(source: string): number[] {
  return (source.match(/-?\d+(?:\.\d+)?/g) ?? []).map(Number);
}

/** X coordinates of a point list, every second number starting at the first. */
function xsOf(values: readonly number[]): number[] {
  return values.filter((_, index) => index % 2 === 0);
}

/** Y coordinates of a point list, every second number starting at the second. */
function ysOf(values: readonly number[]): number[] {
  return values.filter((_, index) => index % 2 === 1);
}

/** The card a node group draws, or `null` when the group is not a card (V-5). */
function readCard(id: string, group: string): Card | null {
  const clipped = group.includes(CLIP_ID_PREFIX);
  const backdrop = BACKDROP.exec(group)?.[1];
  if (!backdrop) return null;

  const pathNumbers = numbers(backdrop);
  const xs = xsOf(pathNumbers);
  const ys = ysOf(pathNumbers);
  if (xs.length === 0 || ys.length === 0) return null;

  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const y0 = Math.min(...ys);
  const y1 = Math.max(...ys);
  const start = /M(-?[\d.]+),(-?[\d.]+)/.exec(backdrop);
  if (!start) return null;

  const radius = Number(start[1]) - x0;
  if (!(radius > 0) || x1 <= x0 || y1 <= y0) return null;

  const fills = [...group.matchAll(FILL)].map((match) => ({ fill: match[1]!, points: match[2]! }));
  if (fills.length === 0) return null;

  const fillValues = fills.flatMap((shape) => numbers(shape.points));
  const fillXs = xsOf(fillValues);
  const fillYs = ysOf(fillValues);
  if (fillXs.length === 0 || fillYs.length === 0) return null;

  const inset = Math.min(Math.min(...fillXs) - x0, Math.min(...fillYs) - y0);
  if (!(inset >= 0)) return null;

  const insetRadius = Math.max(radius - inset, 0);

  return {
    id,
    group,
    contour: { x0, x1, y0, y1, radius },
    fills,
    inset,
    insetRadius,
    clipped,
  };
}

/** Every card the markup draws, in document order. */
export function readCards(svg: string): Card[] {
  const cards: Card[] = [];
  for (const match of svg.matchAll(NODE_GROUP)) {
    const card = readCard(match[1]!, match[2]!);
    if (card !== null) cards.push(card);
  }
  return cards;
}

/** The clip id a card's fills reference. */
export function clipIdFor(card: Card): string {
  return `${CLIP_ID_PREFIX}${card.id}`;
}

/** A number as the markup writes it: at most two decimals, no trailing zeros. */
function round(value: number): string {
  return String(Number(value.toFixed(2)));
}

/** The clip a card's fills reference: its inset contour, as the rounded rectangle it is. */
function clipElement(card: Card): string {
  const x = round(card.contour.x0 + card.inset);
  const y = round(card.contour.y0 + card.inset);
  const width = round(card.contour.x1 - card.contour.x0 - 2 * card.inset);
  const height = round(card.contour.y1 - card.contour.y0 - 2 * card.inset);
  const radius = round(card.insetRadius);
  return `<clipPath id="${clipIdFor(card)}"><rect x="${x}" y="${y}" width="${width}" height="${height}" rx="${radius}"/></clipPath>`;
}

/** The body of a card with the clip inserted and every fill pointing at it. */
function trimmedBody(card: Card): string {
  const id = clipIdFor(card);
  const clipped = `${clipElement(card)}${card.group}`;
  return clipped.replace(/<polygon\b[^>]*\bpoints="[^"]*"/g, (tag) =>
    tag.replace("<polygon ", `<polygon clip-path="url(#${id})" `),
  );
}

/**
 * Trim every card's fills to its inset contour.
 *
 * The markup is changed by insertion only: a `<clipPath>` per card and one `clip-path` reference
 * per fill. Remove those and the input is byte-identical — which is what proofs of "nothing else
 * changed" hang on. A card that already carries the clip is left alone, so the pass is idempotent;
 * markup it does not recognise passes through untouched.
 */
export function containNodeFills(svg: string): string {
  try {
    return svg.replace(NODE_GROUP, (whole: string, id: string, body: string) => {
      const card = readCard(id, body);
      if (card === null || card.clipped) return whole;
      return whole.replace(body, () => trimmedBody(card));
    });
  } catch {
    return svg;
  }
}
