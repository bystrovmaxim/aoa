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

/** Virtual paths registered via ``Graphviz.layout(..., { files })`` — WASM Graphviz does not render ``data:`` URLs in HTML labels. */
export type DomainUseCaseGraphvizFile = { path: string; data: string };

export type DomainUseCaseDotBundle = {
  dot: string;
  files: DomainUseCaseGraphvizFile[];
};

/**
 * Build DOT for a use-case slice. Actions are native ellipses; roles use an SVG actor via ``<IMG>``.
 * The bundle includes ``files`` for future WASM virtual assets (empty when none are emitted).
 */
export function buildDomainUseCaseDotBundle(
  data: DomainUseCaseDiagramPayload,
  rankdir: DomainUseCaseRankdir = "LR",
  imageOptions: DomainUseCaseDotImageOptions,
): DomainUseCaseDotBundle {
  const { actions, roles, edges } = data;
  const files: DomainUseCaseGraphvizFile[] = [];
  const lines: string[] = [
    "digraph use_case {",
    `  graph [rankdir=${rankdir}, bgcolor=transparent, fontname="Inter, Helvetica, sans-serif"];`,
    '  node [fontname="Inter, Helvetica, sans-serif"];',
    '  edge [fontname="Inter, Helvetica, sans-serif"];',
  ];

  // Neutral contour — diagram may mix actions from several domains (see per-node accent_color).
  lines.push(`  subgraph cluster_scope {`);
  lines.push(`    label="";`);
  lines.push(`    style="rounded";`);
  lines.push(`    color="#64748b";`);
  lines.push(`    fontcolor="#0f172a";`);
  lines.push(`    fillcolor="#ffffff";`);
  lines.push(`    penwidth=1.2;`);

  for (const a of actions) {
    const nid = domainUseCaseDotNodeId("a", a.id);
    const lbl = dotEscLabel(a.short_label || a.label);
    const fill = a.accent_color;
    lines.push(
      `    ${nid} [shape=ellipse style="filled" fillcolor="${fill}22" color="${fill}" penwidth=1.2 label="${lbl}" fontsize=11];`,
    );
  }
  lines.push(`  }`);

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
  return { dot: lines.join("\n"), files };
}
