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
  /** Interchange qualname of the closed dictionary this field references, when it references one. */
  reference_qualname?: string | null;
  /** The full annotation, for the type cell's tooltip; absent from a service on an older aoa-action-machine. */
  annotation?: string | null;
};

export type ErdEntity = {
  id: string;
  label?: string;
  color?: string;
  /** The kind word the graph states for this table (``unknown`` when it states none). */
  entity_kind?: string;
  /** The kind's display name, from ``list-entity-kinds``; the header icon's tooltip. */
  entity_kind_label?: string;
  /**
   * The values a closed dictionary declares, in declaration order — carried by the payload
   * and by the graph for every consumer; the card does not draw them.
   */
  values?: ErdValue[];
  /** Interchange domain qualname (for legend / filter when 1-hop adds neighbors). */
  domain_qualname?: string;
  fields?: ErdField[];
};

/** One value of a closed dictionary, as the entity card shows it. */
export type ErdValue = {
  code: string;
  display_name: string;
  properties?: { name: string; value: string }[];
};

export type ErdRelation = {
  source: string;
  target: string;
  label?: string;
  /** `specialization` marks the line into an axis container; `generalization` marks an extension's inheritance line into its head; anything else is an ordinary link. */
  relationship_kind?: string;
  /** Cardinality of the source end — `one`, `zero_one`, `one_many` or `zero_many` — drawn as its crow's-foot end. */
  source_cardinality?: string;
  /** Cardinality of the target end. */
  target_cardinality?: string;
  /** The field on the source table that points at the target: the role written at the target's end. */
  source_field?: string | null;
  /** Its declared inverse on the target table, or null: the role written at the source's end. */
  target_field?: string | null;
};

/** Id Graphviz writes on the ``k``-th relation's edge group, so the post-pass finds its fields. */
export const erdEdgeId = (k: number) => `re${k}`;

/**
 * The crow's-foot end for a cardinality, as Graphviz arrow shapes, the first one nearest the table
 * (spec 029, FR-043): exactly one — two bars; zero or one — a bar and a ring; one or many — a crow's
 * foot and a bar; zero or many — a crow's foot and a ring. An unknown value reads as zero or many.
 */
export const ERD_ENDS: Readonly<Record<string, string>> = {
  one: "teetee",
  zero_one: "teeodot",
  one_many: "crowtee",
  zero_many: "crowodot",
};

function erdEnd(cardinality: string | undefined): string {
  return ERD_ENDS[cardinality ?? ""] ?? ERD_ENDS.zero_many!;
}

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

/**
 * Minimum width of a table's header cell, in points: a short table is as wide as the mockup's card
 * (168 px at a 9 px field font ≈ 205–212 pt at 11 pt fields and a 12 pt header), not a stub.
 */
export const ERD_TABLE_MIN_WIDTH_PT = 210;

/** Side of the square slot the header's kind icon is drawn into, in points. */
export const ERD_KIND_SLOT_PT = 13;

/**
 * The table style of spec 028 (FR-110 … FR-115; mockup screen 21), in diagram units: the header 30 and a
 * row 20 high, the key words in their colours, every second row tinted with the domain colour at 6 %.
 */
export const ERD_HEADER_HEIGHT_PT = 30;
export const ERD_ROW_HEIGHT_PT = 20;
export const ERD_PK_COLOUR = "#b45309";
export const ERD_FK_COLOUR = "#475569";
export const ERD_TYPE_COLOUR = "#64748b";
/** The alpha appended to a domain colour for a tinted row: 0x0f / 0xff ≈ 6 %. */
export const ERD_ROW_TINT_ALPHA = "0f";
/**
 * The card of spec 029 (FR-032; the mockup of spec 028, screen 21): one rounded outline of this radius
 * and width, shared by the header, which fills up to it with no gap.
 */
export const ERD_CARD_RADIUS = 9;
export const ERD_CARD_STROKE = 1.4;

/**
 * Ids of the cells the SVG post-pass looks up. Graphviz writes a cell's ``ID`` into the SVG only with a
 * ``TOOLTIP`` (or ``HREF``), as ``<g id="a_<ID>">`` around the cell's fill and text — the node name is
 * not part of it — so every id carries the table's index and is unique across the drawing.
 */
export const erdCellId = {
  header: (table: number) => `hd${table}`,
  kindSlot: (table: number) => `ks${table}`,
  headerName: (table: number) => `hn${table}`,
  fieldName: (table: number, row: number) => `fn${table}_${row}`,
  fieldType: (table: number, row: number) => `ft${table}_${row}`,
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

// ── Field types as one clean name ────────────────────────────────────────
// A field's type as one clean name, from whatever a service sends (spec 029, FR-030, FR-031). A service
// on the current aoa-action-machine sends the clean name already (``str | None``, ``CurrencyEnumEntity``,
// ``X[]``) and passes through unchanged; an older one sends Python's own spelling — ``UnionType[str,
// NoneType]``, ``Optional[str]``, ``AssociationOne[X]``, ``Generalization[X]``, ``Specialization[Union[A,
// B], K]``, ``list[X]``, ``Literal[a, b]`` — which is rewritten by the same rules. Kept here, not in a
// module of its own, because the drawing checks run this file in plain Node, where it imports no value.

const ONE_RELATIONS = new Set(["AssociationOne", "CompositeOne", "AggregateOne", "Generalization"]);
const MANY_RELATIONS = new Set(["AssociationMany", "CompositeMany", "AggregateMany"]);
const COLLECTIONS = new Set(["list", "set", "frozenset", "List", "Set", "FrozenSet"]);
const UNIONS = new Set(["Union", "UnionType"]);

/** The longest label a row shows; a longer one ends with ``…`` and the tooltip holds the whole. */
export const FIELD_TYPE_MAX_CHARS = 40;

/** Split ``text`` on ``separator`` outside brackets. */
function splitTop(text: string, separator: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let start = 0;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (ch === "[") depth += 1;
    else if (ch === "]") depth -= 1;
    else if (depth === 0 && text.startsWith(separator, i)) {
      parts.push(text.slice(start, i));
      start = i + separator.length;
      i += separator.length - 1;
    }
  }
  parts.push(text.slice(start));
  return parts.map((part) => part.trim()).filter((part) => part !== "");
}

/** ``Name[args]`` as its name and its top-level arguments, or ``null`` when ``text`` is not one. */
function generic(text: string): { name: string; args: string[] } | null {
  const open = text.indexOf("[");
  if (open <= 0 || !text.endsWith("]")) return null;
  return { name: text.slice(0, open).trim(), args: splitTop(text.slice(open + 1, -1), ",") };
}

/** Members of a union joined by ``|``, ``None`` once and last. */
function union(members: string[]): string {
  const clean = members.map(cleanFieldType);
  const others = clean.filter((member) => member !== "None");
  return [...others, ...(others.length < clean.length ? ["None"] : [])].join(" | ");
}

/** A literal value as a value: a number as it is, anything else quoted once. */
function literalValue(value: string): string {
  if (/^-?\d+(\.\d+)?$/.test(value) || value === "True" || value === "False" || value === "None") return value;
  return value.startsWith('"') ? value : `"${value.replace(/^'|'$/g, "")}"`;
}

/** The clean name for a generic, or ``null`` when no rule applies. */
function cleanGeneric(name: string, args: string[]): string | null {
  if (UNIONS.has(name)) return union(args);
  if (name === "Optional" && args.length === 1) return union([args[0]!, "None"]);
  if ((ONE_RELATIONS.has(name) || name === "Specialization") && args.length >= 1) return cleanFieldType(args[0]!);
  if ((MANY_RELATIONS.has(name) || COLLECTIONS.has(name)) && args.length === 1) return `${cleanFieldType(args[0]!)}[]`;
  if ((name === "tuple" || name === "Tuple") && args.length === 2 && args[1] === "...") return `${cleanFieldType(args[0]!)}[]`;
  if (name === "Literal") return args.map(literalValue).join(" | ");
  if (name === "Annotated" && args.length >= 1) return cleanFieldType(args[0]!);
  return null;
}

/** One clean name for the type string ``raw``, as a row shows it. */
export function cleanFieldType(raw: string): string {
  const text = raw.trim();
  if (text === "NoneType") return "None";
  const members = splitTop(text, "|");
  if (members.length > 1) return union(members);
  const parsed = generic(text);
  if (!parsed) return text;
  const clean = cleanGeneric(parsed.name, parsed.args);
  return clean ?? `${parsed.name}[${parsed.args.map(cleanFieldType).join(", ")}]`;
}

/** ``label`` cut to fit a row, ending with ``…`` when it was longer. */
export function fitFieldType(label: string, max = FIELD_TYPE_MAX_CHARS): string {
  return label.length <= max ? label : `${label.slice(0, max - 1)}…`;
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
  const tableIndex = new Map((entities ?? []).map((e, i) => [e.id, i]));

  const nodeSource = (nd: ErdEntity): string => {
    const color = nd.color || "#3b82f6";
    const table = tableIndex.get(nd.id) ?? 0;
    const kind = nd.entity_kind?.trim() || "unknown";
    const kindLabel = nd.entity_kind_label || kind.charAt(0).toUpperCase() + kind.slice(1);

    const rows = (nd.fields || [])
      .map((f, row) => {
        // Every second row carries the domain colour faintly; keys are told by their word, not by a fill.
        const bg = row % 2 === 1 ? `${color}${ERD_ROW_TINT_ALPHA}` : "#ffffff";
        const icon = f.primary_key ? "PK" : f.foreign_key ? "FK" : "";
        const iconColour = f.primary_key ? ERD_PK_COLOUR : ERD_FK_COLOUR;
        const iconTd = icon
          ? `<TD BGCOLOR="${bg}" ALIGN="LEFT" WIDTH="28" HEIGHT="${ERD_ROW_HEIGHT_PT}"><FONT POINT-SIZE="8.5" COLOR="${iconColour}"><B>${icon}</B></FONT></TD>`
          : `<TD BGCOLOR="${bg}" WIDTH="28" HEIGHT="${ERD_ROW_HEIGHT_PT}"></TD>`;
        // A specialization axis row collapses its alternatives into "Specialization N+"
        // and carries the full list as the cell's hover tooltip. The line already says what a field
        // references, so the type cell carries no "→ target" of its own.
        // Any other type reads as one clean name, cut to the column; the tooltip holds the full annotation
        // (spec 029, FR-030).
        const specialization = parseSpecializationType(f.type || "");
        const typeText = specialization !== null ? `Specialization ${specialization.alternatives.length}+` : fitFieldType(cleanFieldType(f.type || ""));
        const tooltipAttr =
          specialization !== null
            ? ` TOOLTIP="${specialization.alternatives
                .map((alt) => `${alt.code} → ${resolveTableLabel(alt.name, entities ?? [])}`)
                .map(escHtml)
                .join("&#10;")}"`
            : ` TOOLTIP="${escHtml(f.annotation || f.type || "")}"`;
        return (
          "<TR>" +
          iconTd +
          `<TD BGCOLOR="${bg}" ALIGN="LEFT" ID="${erdCellId.fieldName(table, row)}" TOOLTIP="Click to copy">${escHtml(f.name)}</TD>` +
          `<TD BGCOLOR="${bg}" ALIGN="RIGHT" ID="${erdCellId.fieldType(table, row)}"${tooltipAttr}><FONT COLOR="${ERD_TYPE_COLOUR}" POINT-SIZE="10">${escHtml(typeText)}</FONT></TD>` +
          "</TR>"
        );
      })
      .join("\n      ");

    return (
      `  "${nd.id}" [label=<<TABLE BGCOLOR="white" BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" STYLE="ROUNDED" COLOR="${color}">` +
      // One header cell with the domain fill, flush with the frame (the card's rounding trims it);
      // inside, the kind icon slot and the name, each filled with the same colour so Graphviz emits
      // their boxes. The post-pass puts icon and name at the left, after an inset (FR-110).
      `<TR><TD COLSPAN="3" BGCOLOR="${color}" ALIGN="LEFT" WIDTH="${ERD_TABLE_MIN_WIDTH_PT}" HEIGHT="${ERD_HEADER_HEIGHT_PT}" ` +
      `ID="${erdCellId.header(table)}" TOOLTIP="${escHtml(nd.label || nd.id)}">` +
      `<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0"><TR>` +
      `<TD ID="${erdCellId.kindSlot(table)}" TOOLTIP="${escHtml(kindLabel)}" BGCOLOR="${color}" ` +
      `WIDTH="${ERD_KIND_SLOT_PT}" HEIGHT="${ERD_KIND_SLOT_PT}" FIXEDSIZE="TRUE"></TD>` +
      `<TD WIDTH="4"></TD>` +
      `<TD ID="${erdCellId.headerName(table)}" TOOLTIP="Click to copy" BGCOLOR="${color}">` +
      `<FONT COLOR="white" POINT-SIZE="12.5"><B>${escHtml(nd.label || nd.id)}</B></FONT></TD>` +
      `</TR></TABLE></TD></TR>${rows}</TABLE>>]`
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
      // See-through but half a tone darker than the canvas, with an outline one point wider than before.
      '    style="rounded,dashed,filled";',
      '    fillcolor="#0f172a0d";',
      '    penwidth=2;',
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
  (relations ?? []).forEach((ed, k) => {
    // The axis relation is already carried by the head's field row ("details (by variant_code)")
    // and by the container that holds the alternatives — no edge is drawn for it.
    if (ed.relationship_kind === "specialization") return;
    const id = `id="${erdEdgeId(k)}" `;
    if (ed.relationship_kind === "generalization" || !ed.source_field) {
      // A generalization is dashed with a filled arrowhead (FR-115); a row from an older server keeps
      // its middle label and gets the plain filled arrowhead.
      const label = ed.label ? `label="${escHtml(ed.label)}" fontsize=9 ` : "";
      const arrow = ed.relationship_kind === "generalization" ? "style=dashed arrowhead=normal " : "arrowhead=normal ";
      lines.push(`  "${ed.source}" -> "${ed.target}" [${`${id}${label}${arrow}`.trim()}]`);
      return;
    }
    // One association, read the ERD way: each end shows how many of the table it touches, and the
    // role that table plays is written next to it; nothing in the middle.
    const tail = ed.target_field ? ` taillabel="${escHtml(ed.target_field)}"` : "";
    lines.push(
      `  "${ed.source}" -> "${ed.target}" [${id}dir=both arrowtail=${erdEnd(ed.source_cardinality)} ` +
        `arrowhead=${erdEnd(ed.target_cardinality)} headlabel="${escHtml(ed.source_field)}"${tail} labelfontsize=9]`,
    );
  });
  lines.push("}");
  return lines.join("\n");
}
