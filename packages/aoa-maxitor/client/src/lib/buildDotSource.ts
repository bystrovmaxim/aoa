// src/lib/buildDotSource.ts
/**
 * Graphviz DOT source for ERD tables — port of the legacy inline ``buildDotSource`` helper
 * (Graphviz renderer only; other engines omitted).
 */

export type ErdField = {
  name: string;
  type?: string;
  primary_key?: boolean;
  foreign_key?: boolean;
};

export type ErdEntity = {
  id: string;
  label?: string;
  color?: string;
  /** Interchange domain qualname (for legend / filter when 1-hop adds neighbors). */
  domain_qualname?: string;
  fields?: ErdField[];
};

export type ErdRelation = {
  source: string;
  target: string;
  label?: string;
};

export type ErdGraphPayload = {
  entities: ErdEntity[];
  relations: ErdRelation[];
};

/** Layout presets matching the old ``activeLayout`` Graphviz branch. */
export type ErdGraphvizLayout = "gv-dot-lr" | "gv-dot-tb" | "gv-neato" | "gv-fdp" | "gv-circo";

function escHtml(s: string): string {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Map UI layout preset to the Graphviz layout engine name passed to ``layout()`` */
export function erdGraphvizEngine(layout: ErdGraphvizLayout): string {
  if (layout === "gv-neato") return "neato";
  if (layout === "gv-fdp") return "fdp";
  if (layout === "gv-circo") return "circo";
  return "dot";
}

export function buildDotSource(data: ErdGraphPayload, layout: ErdGraphvizLayout): string {
  const { entities, relations } = data;
  const isLR = layout === "gv-dot-lr";
  const lines: string[] = ["digraph ERD {"];

  if (layout === "gv-neato") {
    lines.push(
      '  graph [fontname="Helvetica" bgcolor=transparent pad="0.5" overlap=false splines=false sep="+40"]',
    );
  } else {
    lines.push(
      `  graph [rankdir=${isLR ? "LR" : "TB"} fontname="Helvetica" bgcolor=transparent pad="0.5" nodesep="0.8" ranksep="1.2"]`,
    );
  }
  lines.push(
    '  node  [shape=none fontname="Helvetica" fontsize=11 margin="0"]',
    '  edge  [fontname="Helvetica" fontsize=9 color="#94a3b8" arrowsize=0.7]',
    "",
  );

  for (const nd of entities ?? []) {
    const color = nd.color || "#3b82f6";
    const rows = (nd.fields || [])
      .map((f) => {
        const bg = f.primary_key ? "#fef9c3" : f.foreign_key ? "#dbeafe" : "#ffffff";
        const icon = f.primary_key ? "PK" : f.foreign_key ? "FK" : "";
        const iconTd = icon
          ? `<TD BGCOLOR="${bg}" ALIGN="CENTER" WIDTH="28"><FONT POINT-SIZE="9"><B>${icon}</B></FONT></TD>`
          : `<TD BGCOLOR="${bg}" WIDTH="28"></TD>`;
        return (
          "<TR>" +
          iconTd +
          `<TD BGCOLOR="${bg}" ALIGN="LEFT">${escHtml(f.name)}</TD>` +
          `<TD BGCOLOR="${bg}" ALIGN="LEFT"><FONT COLOR="#64748b"><I>${escHtml(f.type || "")}</I></FONT></TD>` +
          "</TR>"
        );
      })
      .join("\n      ");

    lines.push(
      `  "${nd.id}" [label=<<TABLE BGCOLOR="white" BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" STYLE="ROUNDED" COLOR="${color}">` +
        `<TR><TD COLSPAN="3" BGCOLOR="${color}" ALIGN="CENTER">` +
        `<FONT COLOR="white" POINT-SIZE="12"><B>${escHtml(nd.label || nd.id)}</B></FONT>` +
        `</TD></TR>${rows}</TABLE>>]`,
    );
  }

  lines.push("");
  for (const ed of relations ?? []) {
    const lbl = ed.label ? ` [label="${escHtml(ed.label)}" fontsize=9]` : "";
    lines.push(`  "${ed.source}" -> "${ed.target}"${lbl}`);
  }
  lines.push("}");
  return lines.join("\n");
}
