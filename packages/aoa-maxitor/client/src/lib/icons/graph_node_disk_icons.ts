// src/lib/icons/graph_node_disk_icons.ts
/**
 * App-wide Lucide-derived SVG ``data:`` URLs for Action Machine graph node types (colored
 * disk + glyph, or transparent glyph for stacked canvas layers such as G6).
 *
 * Paths match ``lucide-static`` (ISC, https://github.com/lucide-icons/lucide).
 */

const ERROR_HANDLER_INNER_STROKE = "#B45309";

const LUCIDE_CONTEXT_FORK_INNER =
  '<path d="M12 22v-5" /> ' +
  '<path d="M9 8V2" /> ' +
  '<path d="M15 8V2" /> ' +
  '<path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z" />';

const LUCIDE_BRACES_OUTLINE =
  '<path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5c0 1.1.9 2 2 2h1" /> ' +
  '<path d="M16 21h1a2 2 0 0 0 2-2v-5c0-1.1.9-2 2-2a2 2 0 0 1-2-2V5a2 2 0 0 0-2-2h-1" />';

const LUCIDE_FIELD_BRACES_INNER =
  LUCIDE_BRACES_OUTLINE + '<path d="M9 7.5v9M9 7.5h5.5M9 11.5h4" />';
const LUCIDE_PROPERTY_FIELD_BRACES_INNER =
  LUCIDE_BRACES_OUTLINE +
  '<path d="M9.5 8.5V17M9.5 8.5h3.8a2.1 2.1 0 0 1 0 4.2H9.5" />';

/** Inner elements only (no ``<svg>`` wrapper), keyed by graph ``node_type`` strings. */
const GRAPH_NODE_TYPE_LUCIDE_INNER_SVG: Record<string, string> = {
  Application:
    '<rect width="7" height="9" x="3" y="3" rx="1" /> ' +
    '<rect width="7" height="5" x="14" y="3" rx="1" /> ' +
    '<rect width="7" height="9" x="14" y="12" rx="1" /> ' +
    '<rect width="7" height="5" x="3" y="16" rx="1" />',
  Action:
    '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />',
  Domain:
    '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" /> ' +
    '<path d="m3.3 7 8.7 5 8.7-5" /> ' +
    '<path d="M12 22V12" />',
  RequiredContext: LUCIDE_CONTEXT_FORK_INNER,
  RegularAspect:
    '<path d="m3 16 4 4 4-4" /> ' +
    '<path d="M7 20V4" /> ' +
    '<path d="M11 4h10" /> ' +
    '<path d="M11 8h7" /> ' +
    '<path d="M11 12h4" />',
  SummaryAspect:
    '<path d="m3 8 4-4 4 4" /> ' +
    '<path d="M7 4v16" /> ' +
    '<path d="M11 12h4" /> ' +
    '<path d="M11 16h7" /> ' +
    '<path d="M11 20h10" />',
  Checker:
    '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z" /> ' +
    '<path d="m9 12 2 2 4-4" />',
  Compensator:
    '<path d="M9 14 4 9l5-5" /> ' +
    '<path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11" />',
  ErrorHandler:
    '<path fill="none" stroke="' +
    ERROR_HANDLER_INNER_STROKE +
    '" d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" /> ' +
    '<path fill="none" stroke="' +
    ERROR_HANDLER_INNER_STROKE +
    '" d="M12 9v4" /> ' +
    '<path fill="none" stroke="' +
    ERROR_HANDLER_INNER_STROKE +
    '" d="M12 17h.01" />',
  Entity:
    '<ellipse cx="12" cy="5" rx="9" ry="3" /> ' +
    '<path d="M3 5V19A9 3 0 0 0 21 19V5" /> ' +
    '<path d="M3 12A9 3 0 0 0 21 12" />',
  Lifecycle:
    '<circle cx="18" cy="6" r="3" /> ' +
    '<circle cx="6" cy="18" r="3" /> ' +
    '<path d="M18 9v1a4 4 0 0 1-4 4H9a4 4 0 0 0-4 4v1" />',
  StateInitial:
    '<circle cx="12" cy="12" r="9" /> ' +
    '<circle cx="12" cy="12" r="3" fill="#ffffff" stroke="none" />',
  StateIntermediate: '<circle cx="12" cy="12" r="9" /> ' + '<circle cx="12" cy="12" r="4" />',
  StateFinal:
    '<circle cx="12" cy="12" r="9" /> ' + '<path d="m8 12 2 2 4-4" />',
  Resource:
    '<line x1="22" x2="2" y1="12" y2="12" /> ' +
    '<path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" /> ' +
    '<line x1="6" x2="6.01" y1="16" y2="16" /> ' +
    '<line x1="10" x2="10.01" y1="16" y2="16" />',
  Role:
    '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />',
  Sensitive:
    '<rect width="18" height="11" x="3" y="11" rx="2" ry="2" /> ' +
    '<path d="M7 11V7a5 5 0 0 1 10 0v4" />',
  Params:
    '<path d="M17 12H3" /> ' + '<path d="m11 18 6-6-6-6" /> ' + '<path d="M21 5v14" />',
  Result:
    '<path d="M3 19V5" /> ' + '<path d="m13 6-6 6 6 6" /> ' + '<path d="M7 12h14" />',
  Field: LUCIDE_FIELD_BRACES_INNER,
  PropertyField: LUCIDE_PROPERTY_FIELD_BRACES_INNER,
  unknown: LUCIDE_CONTEXT_FORK_INNER,
};

const ERROR_HANDLER_NODE_TYPE = "ErrorHandler";

const ICON_INNER_SCALE = 0.58;
const ICON_STROKE_WIDTH = 2.0 / ICON_INNER_SCALE;

function svgDataUri(svg: string): string {
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function innerForNodeType(nodeType: string): string {
  const nt = nodeType.trim();
  return GRAPH_NODE_TYPE_LUCIDE_INNER_SVG[nt] ?? GRAPH_NODE_TYPE_LUCIDE_INNER_SVG.unknown;
}

/** Transparent glyph for G6 ``circle`` nodes (fill comes from node ``style``). */
export function svgDataUriForGraphNodeGlyphOnly(nodeType: string): string {
  const nt = String(nodeType).trim();
  const inner = innerForNodeType(nt);
  const strokeHex = nt === ERROR_HANDLER_NODE_TYPE ? ERROR_HANDLER_INNER_STROKE : "#ffffff";
  const s = ICON_INNER_SCALE;
  const sw = ICON_STROKE_WIDTH;
  const gOpen =
    `<g transform="translate(12,12) scale(${s}) translate(-12,-12)" ` +
    `fill="none" stroke="${strokeHex}" stroke-width="${sw.toFixed(4)}" ` +
    `stroke-linecap="round" stroke-linejoin="round">`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">${gOpen}${inner}</g></svg>`;
  return svgDataUri(svg);
}

/** Colored 24×24 disk with white glyph (ErrorHandler keeps amber inner strokes on paths). */
export function svgDataUriForGraphNodeIcon(fillHex: string, nodeType: string): string {
  const inner = innerForNodeType(String(nodeType).trim());
  const s = ICON_INNER_SCALE;
  const sw = ICON_STROKE_WIDTH;
  const gOpen =
    `<g transform="translate(12,12) scale(${s}) translate(-12,-12)" ` +
    `fill="none" stroke="#ffffff" stroke-width="${sw.toFixed(4)}" ` +
    `stroke-linecap="round" stroke-linejoin="round">`;
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">` +
    `<circle cx="12" cy="12" r="11" fill="${fillHex}"/>` +
    `${gOpen}${inner}</g></svg>`;
  return svgDataUri(svg);
}

/** Domain node disk for pickers and legends (same glyph as graph ``Domain`` rows). */
export function svgDataUriForInterchangeDomainLegend(fillHex: string): string {
  return svgDataUriForGraphNodeIcon(fillHex, "Domain");
}
