// src/lib/icons/entity_kind_glyphs.ts
/**
 * Entity kind icons for the ERD: a pictogram for each kind word Maxitor knows, a monogram for any other.
 *
 * This is presentation only. The set of kinds, their order and their names come from the loaded graph
 * (``list-entity-kinds``); this file only decides how a known word is drawn, and it is the one place in
 * Maxitor that names AOA's kind words. Deleting an entry changes that kind's picture to a monogram and
 * nothing else.
 *
 * Glyphs are 24×24 stroke paths in the Lucide style of ``graph_node_disk_icons.ts``.
 */

/** Stroke paths per known kind word. */
const KIND_GLYPHS: Readonly<Record<string, string>> = {
  // The record itself: a table with a header bar.
  core: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9.5h18"/>',
  // A link between two objects.
  assoc: '<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><path d="M8 12h8"/>',
  // A part hanging off its owner.
  detail: '<path d="M5 3v8a4 4 0 0 0 4 4h11"/><path d="m15 10 5 5-5 5"/>',
  // A layer over its base.
  spec:
    '<path d="m16.02 12 5.48 3.13a1 1 0 0 1 0 1.74L13 21.74a2 2 0 0 1-2 0l-8.5-4.87a1 1 0 0 1 0-1.74L7.98 12"/>' +
    '<path d="M13 13.74a2 2 0 0 1-2 0L2.5 8.87a1 1 0 0 1 0-1.74L11 2.26a2 2 0 0 1 2 0l8.5 4.87a1 1 0 0 1 0 1.74Z"/>',
  // A set of fixed values.
  enum: '<path d="M9 6h12M9 12h12M9 18h12"/><path d="M4 6h.01M4 12h.01M4 18h.01" stroke-width="3.6"/>',
  // A lifecycle state.
  state: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.5"/>',
  // Maxitor's own placeholder for a row whose producer stated no kind.
  unknown: '<circle cx="12" cy="12" r="9.5"/><path d="M9.2 9.2a2.9 2.9 0 0 1 5.6 1c0 2-2.8 2.6-2.8 4"/><path d="M12 17.6h.01" stroke-width="3"/>',
};

/** Glyphs that fill their box edge to edge read larger than the rest; they are drawn at this share of it. */
const KIND_GLYPH_SCALE: Readonly<Record<string, number>> = { spec: 0.8 };

/** The grey every kind's legend disk uses: no kind takes a domain hue. */
export const KIND_DISK_FILL = "#94a3b8";

function escapeXml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/**
 * The inner SVG of a kind's icon in a 24×24 box: its pictogram stroked with ``ink``, or the word's
 * first two letters when Maxitor does not know the word.
 */
export function kindGlyphSvg(word: string, ink: string, strokeWidth: number): string {
  const glyph = KIND_GLYPHS[word];
  if (glyph === undefined) {
    return (
      `<text x="12" y="16.2" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="11.5" ` +
      `font-weight="700" fill="${ink}">${escapeXml(word.slice(0, 2))}</text>`
    );
  }
  const scale = KIND_GLYPH_SCALE[word] ?? 1;
  const transform = scale === 1 ? "" : ` transform="translate(12,12) scale(${scale}) translate(-12,-12)"`;
  return (
    `<g${transform} fill="none" stroke="${ink}" stroke-width="${(strokeWidth / scale).toFixed(3)}" ` +
    `stroke-linecap="round" stroke-linejoin="round">${glyph}</g>`
  );
}

/** The kind's legend disk: a grey disk with the white glyph, drawn like a domain's disk. */
export function kindLegendDiskUri(word: string): string {
  const scale = 0.58;
  const inner = kindGlyphSvg(word, "#ffffff", 2 / scale);
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">` +
    `<circle cx="12" cy="12" r="11" fill="${KIND_DISK_FILL}"/>` +
    `<g transform="translate(12,12) scale(${scale}) translate(-12,-12)">${inner}</g></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
