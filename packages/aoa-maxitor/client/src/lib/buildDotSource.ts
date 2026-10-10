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
  /** `specialization` marks the line into an axis container; `generalization` marks an extension's inheritance line into its head; anything else is an ordinary link. */
  relationship_kind?: string;
};

/**
 * One specialization axis, drawn as a Graphviz cluster around its alternatives.
 *
 * A group is a **drawing, not a table** — its members keep their own nodes, columns and outside
 * relations — and it belongs to the ERD only. No other diagram reads this field, and the full
 * graph has no notion of one.
 */
export type ErdGroup = {
  group_id: string;
  label: string;
  classifier_field?: string;
  members: string[];
};

export type ErdGraphPayload = {
  entities: ErdEntity[];
  relations: ErdRelation[];
  groups?: ErdGroup[];
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

/**
 * Parse the axis row's type cell — ``"A (code_a) | B (code_b)"`` — into its
 * alternatives (code + short name each). Returns ``null`` for rows that are
 * not a specialization axis.
 */
function parseSpecializationType(type: string): { alternatives: Array<{ code: string; name: string }> } | null {
  const parts = type.split(" | ");
  if (parts.length < 2) return null;
  const alternatives: Array<{ code: string; name: string }> = [];
  for (const part of parts) {
    const open = part.lastIndexOf(" (");
    const close = part.lastIndexOf(")");
    if (open < 0 || close < open) return null;
    alternatives.push({ name: part.slice(0, open).trim(), code: part.slice(open + 2, close).trim() });
  }
  return { alternatives };
}

/**
 * Resolve a wire short label to the full table label of the entity it names.
 */
function resolveTableLabel(name: string, entities: ErdEntity[]): string {
  for (const e of entities) {
    if (e.label === name) return e.label;
    if (e.label?.replace(/Entity$/, "") === name) return e.label;
    if (e.id.endsWith(`.${name}`)) return e.label || name;
  }
  return name;
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
  const groups = data.groups ?? [];
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

  // A member is declared inside its cluster and nowhere else: Graphviz gives a node to the first
  // subgraph that declares it, so declaring it twice would silently drop it out of the container.
  const grouped = new Set<string>();
  for (const group of groups) {
    for (const member of group.members) grouped.add(member);
  }
  const entityById = new Map((entities ?? []).map((e) => [e.id, e]));

  const nodeSource = (nd: ErdEntity): string => {
    const color = nd.color || "#3b82f6";
    const rows = (nd.fields || [])
      .map((f) => {
        const bg = f.primary_key ? "#fef9c3" : f.foreign_key ? "#dbeafe" : "#ffffff";
        const icon = f.primary_key ? "PK" : f.foreign_key ? "FK" : "";
        const iconTd = icon
          ? `<TD BGCOLOR="${bg}" ALIGN="CENTER" WIDTH="28"><FONT POINT-SIZE="9"><B>${icon}</B></FONT></TD>`
          : `<TD BGCOLOR="${bg}" WIDTH="28"></TD>`;
        // A specialization axis row collapses its alternatives into "Specialization N+"
        // and carries the full list as the cell's hover tooltip.
        const specialization = parseSpecializationType(f.type || "");
        const typeText = specialization !== null ? `Specialization ${specialization.alternatives.length}+` : f.type || "";
        const tooltipAttr =
          specialization !== null
            ? ` TOOLTIP="${specialization.alternatives
                .map((alt) => `${alt.code} → ${resolveTableLabel(alt.name, entities ?? [])}`)
                .map(escHtml)
                .join("&#10;")}"`
            : "";
        return (
          "<TR>" +
          iconTd +
          `<TD BGCOLOR="${bg}" ALIGN="LEFT">${escHtml(f.name)}</TD>` +
          `<TD BGCOLOR="${bg}" ALIGN="LEFT"${tooltipAttr}><FONT COLOR="#64748b"><I>${escHtml(typeText)}</I></FONT></TD>` +
          "</TR>"
        );
      })
      .join("\n      ");

    return (
      `  "${nd.id}" [label=<<TABLE BGCOLOR="white" BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" STYLE="ROUNDED" COLOR="${color}">` +
      `<TR><TD COLSPAN="3" BGCOLOR="${color}" ALIGN="CENTER">` +
      `<FONT COLOR="white" POINT-SIZE="12"><B>${escHtml(nd.label || nd.id)}</B></FONT>` +
      `</TD></TR>${rows}</TABLE>>]`
    );
  };

  for (const group of groups) {
    const members = group.members
      .map((id) => entityById.get(id))
      .filter((nd): nd is ErdEntity => nd !== undefined);
    if (members.length < 2) continue;
    lines.push(
      `  subgraph "cluster_${group.group_id}" {`,
      `    label="${escHtml(group.label)}";`,
      '    style="rounded,dashed";',
      '    color="#94a3b8";',
      '    fontsize=10;',
      '    margin=12;',
      ...members.map((nd) => nodeSource(nd)),
      "  }",
    );
  }

  for (const nd of entities ?? []) {
    if (grouped.has(nd.id)) continue;
    lines.push(nodeSource(nd));
  }

  lines.push("");
  for (const ed of relations ?? []) {
    const label = ed.label ? `label="${escHtml(ed.label)}" fontsize=9 ` : "";
    const arrow =
      ed.relationship_kind === "specialization"
        ? "arrowhead=vee "
        : ed.relationship_kind === "generalization"
          ? "arrowhead=empty "
          : "";
    const attrs = `${label}${arrow}`.trim();
    lines.push(`  "${ed.source}" -> "${ed.target}"${attrs ? ` [${attrs}]` : ""}`);
  }
  lines.push("}");
  return lines.join("\n");
}
