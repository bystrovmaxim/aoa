// src/lib/buildDomainUseCaseDotSource.ts
import type { DomainUseCaseDiagramPayload } from "@/model/domainUseCaseDiagram";

export type DomainUseCaseRankdir = "LR" | "TB";

/** Must match ``image=`` on role nodes and ``images[].path`` passed to Graphviz WASM. */
export type DomainUseCaseDotImageOptions = {
  roleActorImageUrl: string;
};

/** Stable Graphviz node id from interchange qualname. */
export function domainUseCaseDotNodeId(kind: "a" | "r", qualname: string): string {
  const safe = qualname.replace(/[^0-9A-Za-z_]/g, "_");
  return `${kind}_${safe}`;
}

function dotEscLabel(text: string): string {
  return text.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n");
}

function dotEscAttr(text: string): string {
  return text.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function htmlEsc(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function svgXmlEsc(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/** Solid light fill from accent (replaces translucent ``#RRGGBB22`` alpha overlay). */
function opaqueAccentFill(accentHex: string): string {
  const raw = accentHex.trim();
  const compact = raw.startsWith("#") ? raw.slice(1) : raw;
  if (!/^[0-9a-fA-F]{6}$/.test(compact)) return "#ffffff";
  const n = Number.parseInt(compact, 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  const mix = (c: number) => Math.round(c * 0.12 + 255 * 0.88);
  const toHex = (v: number) => v.toString(16).padStart(2, "0");
  return `#${toHex(mix(r))}${toHex(mix(g))}${toHex(mix(b))}`;
}

/**
 * Wrap label into the minimum number of lines by greedily packing camelCase
 * words onto each line up to ``maxChars`` characters.
 */
function wrapLabel(label: string, maxChars = 15): string[] {
  // Split on camelCase boundaries to get atomic words.
  const words = label.replace(/([a-z])([A-Z])/g, "$1\n$2").split("\n");
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    if (current === "") {
      current = word;
    } else if ((current + word).length <= maxChars) {
      current += word;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  return lines;
}

/**
 * Build a UML-use-case SVG glyph: ellipse with right-side diagonal slash + centred label.
 * Returned as a ``data:image/svg+xml;base64,...`` URL so Graphviz WASM can embed it via
 * ``images: [{ path: dataUrl, width, height }]`` — the browser loads ``href=dataUrl`` fine.
 */
export function buildActionGlyphDataUrl(label: string, accentColor: string): string {
  const lines = wrapLabel(label);
  const lineCount = lines.length;

  const FONT = 11;
  const LINE_H = FONT + 3;
  const PAD_V = 10;
  const H = Math.max(60, lineCount * LINE_H + PAD_V * 2);
  const W = 160;
  const cx = W / 2;
  const cy = H / 2;
  const rx = 74;
  const ry = H / 2 - 4;
  const fill = opaqueAccentFill(accentColor);

  // Right-shifted chord on the ellipse.
  const frac1 = 0.50;
  const frac2 = 0.97;
  const x1 = cx + rx * frac1;
  const y1 = cy + ry * Math.sqrt(1 - frac1 ** 2);
  const x2 = cx + rx * frac2;
  const y2 = cy - ry * Math.sqrt(Math.max(0, 1 - frac2 ** 2));

  const textY0 = cy - ((lineCount - 1) * LINE_H) / 2 + FONT * 0.35;
  const textSvg = lines
    .map((ln, i) =>
      `<text x="${cx}" y="${(textY0 + i * LINE_H).toFixed(2)}" text-anchor="middle" ` +
      `font-family="Inter,Helvetica,sans-serif" font-size="${FONT}" font-weight="600" fill="#0f172a">${svgXmlEsc(ln)}</text>`,
    )
    .join("");

  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">` +
    `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}" stroke="${accentColor}" stroke-width="1.6"/>` +
    textSvg +
    `<line x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}" stroke="${accentColor}" stroke-width="1.3" stroke-linecap="round"/>` +
    `</svg>`;

  const b64 = typeof btoa !== "undefined"
    ? btoa(unescape(encodeURIComponent(svg)))
    : Buffer.from(svg, "utf8").toString("base64");
  return `data:image/svg+xml;base64,${b64}`;
}

/** Virtual paths registered via ``Graphviz.layout(..., { files })`` — WASM Graphviz does not render ``data:`` URLs in HTML labels. */
export type DomainUseCaseGraphvizFile = { path: string; data: string };

export type DomainUseCaseDotBundle = {
  dot: string;
  files: DomainUseCaseGraphvizFile[];
  /** ``images`` entries to pass to ``gv.layout(..., { images })`` — action glyph data URLs. */
  actionImages: Array<{ path: string; width: string; height: string }>;
};

/** Optional layout switches for DOT generation. */
export type DomainUseCaseDotLayoutOptions = {
  /**
   * When true (default), actions are subgraph-clustered behind a rounded system-boundary contour.
   * When false, action nodes lay out without that cluster (UML boundary optional).
   */
  boundary?: boolean;
};

/**
 * Build DOT for a use-case slice. Actions are native ellipses; roles use an SVG actor via ``<IMG>``.
 * The bundle includes ``files`` for future WASM virtual assets (empty when none are emitted).
 */
export function buildDomainUseCaseDotBundle(
  data: DomainUseCaseDiagramPayload,
  rankdir: DomainUseCaseRankdir = "LR",
  imageOptions: DomainUseCaseDotImageOptions,
  layout?: DomainUseCaseDotLayoutOptions,
): DomainUseCaseDotBundle {
  const boundary = layout?.boundary !== false;
  const { actions, roles, edges } = data;
  const files: DomainUseCaseGraphvizFile[] = [];
  const actionImages: Array<{ path: string; width: string; height: string }> = [];
  const lines: string[] = [
    "digraph use_case {",
    `  graph [rankdir=${rankdir}, bgcolor=transparent, fontname="Inter, Helvetica, sans-serif"];`,
    '  node [fontname="Inter, Helvetica, sans-serif"];',
    '  edge [fontname="Inter, Helvetica, sans-serif"];',
  ];

  const pushActionNodes = (indent: string) => {
    for (const a of actions) {
      const nid = domainUseCaseDotNodeId("a", a.id);
      const linesCount = wrapLabel(a.short_label || a.label).length;
      const H = Math.max(60, linesCount * 14 + 20);
      const W = 160;
      const wIn = (W / 96).toFixed(3);
      const hIn = (H / 96).toFixed(3);
      const dataUrl = buildActionGlyphDataUrl(a.short_label || a.label, a.accent_color);
      actionImages.push({ path: dataUrl, width: `${W}px`, height: `${H}px` });
      lines.push(
        `${indent}${nid} [shape=none label="" image="${dotEscAttr(dataUrl)}" width=${wIn} height=${hIn} fixedsize=true];`,
      );
    }
  };

  if (boundary) {
    // Neutral contour — diagram may mix actions from several domains (see per-node accent_color).
    lines.push(`  subgraph cluster_scope {`);
    lines.push(`    label="";`);
    lines.push(`    style="rounded,filled";`);
    lines.push(`    color="#64748b";`);
    lines.push(`    fontcolor="#0f172a";`);
    lines.push(`    fillcolor="#ffffff";`);
    lines.push(`    penwidth=1.2;`);
    pushActionNodes("    ");
    lines.push(`  }`);
  } else {
    pushActionNodes("  ");
  }

  const imgUrl = dotEscAttr(imageOptions.roleActorImageUrl);
  for (const r of roles) {
    const nid = domainUseCaseDotNodeId("r", r.id);
    const rl = htmlEsc(r.short_label || r.label);
    lines.push(
      `  ${nid} [shape=plaintext margin=0 label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="-8" CELLPADDING="0"><TR><TD FIXEDSIZE="TRUE" WIDTH="52" HEIGHT="74"><IMG SRC="${imgUrl}" WIDTH="52" HEIGHT="74"/></TD></TR><TR><TD HEIGHT="12"><FONT POINT-SIZE="10">${rl}</FONT></TD></TR></TABLE>>];`,
    );
  }

  for (const e of edges) {
    const ek = e.edge_kind;
    if (ek === "action_generalization") {
      const s = domainUseCaseDotNodeId("a", e.source_id);
      const t = domainUseCaseDotNodeId("a", e.target_id);
      lines.push(`  ${s} -> ${t} [arrowhead=empty style=solid penwidth=1];`);
    } else if (ek === "role_generalization") {
      const s = domainUseCaseDotNodeId("r", e.source_id);
      const t = domainUseCaseDotNodeId("r", e.target_id);
      lines.push(`  ${s} -> ${t} [arrowhead=empty style=solid penwidth=1];`);
    } else if (ek === "association") {
      const act = domainUseCaseDotNodeId("a", e.source_id);
      const rol = domainUseCaseDotNodeId("r", e.target_id);
      lines.push(`  ${rol} -> ${act} [style=solid penwidth=1 arrowhead=vee];`);
    } else if (ek === "include" || ek === "extend") {
      const s = domainUseCaseDotNodeId("a", e.source_id);
      const t = domainUseCaseDotNodeId("a", e.target_id);
      const lab = e.stereotype ? dotEscLabel(e.stereotype) : ek === "include" ? "\u00abinclude\u00bb" : "\u00abextend\u00bb";
      lines.push(`  ${s} -> ${t} [style=dashed arrowhead=open label="${lab}" fontsize=9 labeldistance=2.5];`);
    } else if (ek === "depends") {
      const s = domainUseCaseDotNodeId("a", e.source_id);
      const t = domainUseCaseDotNodeId("a", e.target_id);
      lines.push(`  ${s} -> ${t} [style=dashed arrowhead=open penwidth=0.8];`);
    }
  }

  lines.push("}");
  return { dot: lines.join("\n"), files, actionImages };
}
