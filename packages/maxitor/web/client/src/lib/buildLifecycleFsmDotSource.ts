// src/lib/buildLifecycleFsmDotSource.ts
import type { DiffStatus } from "../api/compare";
import type { LifecycleFiniteAutomatonPayload, LifecycleFsmArrow } from "../model/lifecycleFiniteAutomaton";

const ENTRY = "__gv_lifecycle_entry";
const EXIT = "__gv_lifecycle_exit";

/** Graphviz inches: entry black dot and final-state glyph share the same bounding box (UML-style). */
const PSEUDO_STATE_WH = "0.28";
const PSEUDO_MARGIN = "0.02";
const PSEUDO_COMMON = `fixedsize=true, width=${PSEUDO_STATE_WH}, height=${PSEUDO_STATE_WH}, margin=${PSEUDO_MARGIN}`;

function dotQuoteId(key: string): string {
  return `"${key.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

function htmlEscape(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/** First word sentence case; remaining words lowercased (per whitespace segments). */
function formatStateTitle(displayName: string, key: string): string {
  const raw = displayName.trim() || key.replace(/_/g, " ");
  const parts = raw.split(/\s+/).filter(Boolean);
  if (!parts.length) return key;
  return parts
    .map((p, i) =>
      i === 0 ? `${p.charAt(0).toUpperCase()}${p.slice(1).toLowerCase()}` : p.toLowerCase(),
    )
    .join(" ");
}

export function paletteForStateType(t: string): { fill: string; stroke: string } {
  if (t === "initial") return { fill: "#ecfdf5", stroke: "#059669" };
  if (t === "final") return { fill: "#f8fafc", stroke: "#64748b" };
  return { fill: "#eff6ff", stroke: "#2563eb" };
}

/** A declared colour, stripped of characters that would break the DOT attribute; the palette otherwise. */
function dotColor(value: unknown, fallback: string): string {
  if (typeof value !== "string") return fallback;
  const cleaned = value.trim().replace(/["\\\n\r]/g, "");
  return cleaned.length > 0 ? cleaned : fallback;
}

export type LifecycleFsmRankdir = "LR" | "TB";

/** The class Graphviz writes on what a comparison leaves unchanged; the viewer turns it grey and dim. */
export const LIFECYCLE_FADED_CLASS = "lifecycle-faded";

/** The colours and signs of a status, here too: the engines' comparison runs this file alone, with nothing else to import. */
const ERD_DIFF_COLOUR = { added: "#16a34a", removed: "#dc2626", changed: "#d97706" } as const;
const ERD_DIFF_SIGN = { added: "+", removed: "−", changed: "~" } as const;

/** The SVG id a marked state or transition is drawn under, which a step goes to. */
export function lifecycleCellId(id: string): string {
  return `change_${id.replace(/[^0-9A-Za-z_]/g, "_")}`;
}

/** The tint inside a marked state. */
const MARK_FILL = { added: "#f0fdf4", removed: "#fef2f2", changed: "#fffbeb" } as const;

/** A state's text in Diff: a plain label is centred, and the margin leaves room for what Graphviz measures short in bold. */
const MARKED_LABEL = `fontname="Helvetica-Bold", margin="0.2,0.08"`;

/** A state in Diff: its status's colour in place of what it declares, its sign in the name, its shape as in One; painted by kinds, the kind fills it and the outline says the status. */
function markedState(key: string, title: string, id: string, diff: DiffStatus, kindPaint: { fill: string; stroke: string } | null): string {
  const tooltip = title.replace(/\\/g, "").replace(/"/g, "'");
  if (diff === "unchanged") {
    return `  ${dotQuoteId(key)} [label="${tooltip}", ${MARKED_LABEL}, shape=box, style="rounded,filled", fillcolor="${kindPaint?.fill ?? "#ffffff"}", color="${kindPaint?.stroke ?? "#64748b"}", penwidth=1.15, class="${LIFECYCLE_FADED_CLASS}", tooltip="${tooltip}"];`;
  }
  const sign = ERD_DIFF_SIGN[diff];
  const colour = ERD_DIFF_COLOUR[diff];
  const line = diff === "removed" ? "rounded,filled,dashed" : "rounded,filled";
  return `  ${dotQuoteId(key)} [label="${sign} ${tooltip}", ${MARKED_LABEL}, shape=box, style="${line}", fillcolor="${kindPaint?.fill ?? MARK_FILL[diff]}", color="${colour}", fontcolor="${colour}", penwidth=1.8, id="${lifecycleCellId(id)}", tooltip="${sign} ${tooltip}"];`;
}

/** A line's attributes in Diff: its status's colour, dashed when removed, or fading. */
function markedLine(diff: DiffStatus, id: string | null): string {
  if (diff === "unchanged") return ` [class="${LIFECYCLE_FADED_CLASS}"]`;
  const colour = ERD_DIFF_COLOUR[diff];
  return ` [color="${colour}", penwidth=1.8${diff === "removed" ? ", style=dashed" : ""}${id ? `, id="${lifecycleCellId(id)}"` : ""}]`;
}

/** A dot takes a status's colour only when every arrow on it has that status; otherwise it stays grey. */
function dotStatus(arrows: readonly LifecycleFsmArrow[]): DiffStatus {
  const [first] = arrows;
  return first && arrows.every((arrow) => arrow.diff === first.diff) ? first.diff : "unchanged";
}

/** The attributes that recolour a dot in Diff. */
function markedDot(diff: DiffStatus): string {
  if (diff === "unchanged") return `, class="${LIFECYCLE_FADED_CLASS}"`;
  return `, fillcolor="${ERD_DIFF_COLOUR[diff]}", color="${ERD_DIFF_COLOUR[diff]}"`;
}

/** DOT source for Graphviz ``dot`` layout (UML-style entry / exit pseudostates). */
export function buildLifecycleFsmDotSource(data: LifecycleFiniteAutomatonPayload, rankdir: LifecycleFsmRankdir = "LR", paintByKinds = false): string {
  const stateKeys = new Set(data.states.map((s) => s.key));
  const initialOk = data.initial_state_keys.filter((k) => stateKeys.has(k));
  const finals = data.states.filter((s) => (s.state_type ?? "") === "final" && stateKeys.has(s.key));
  // In Diff the arrows say what they are; in One they follow the states, as ever.
  const entries = data.entries?.filter((arrow) => stateKeys.has(arrow.key));
  const exits = data.exits?.filter((arrow) => stateKeys.has(arrow.key));
  const hasEntry = entries ? entries.length > 0 : initialOk.length > 0;
  const hasExit = exits ? exits.length > 0 : finals.length > 0;

  const lines: string[] = [];
  lines.push("digraph lifecycle_fsm {");
  lines.push(
    `  graph [rankdir=${rankdir}, bgcolor=transparent, splines=true, nodesep=0.45, ranksep=0.65, fontname="Helvetica Neue"];`,
  );
  lines.push('  node [fontname="Helvetica Neue", fontsize=11];');
  lines.push('  edge [color="#64748b", arrowsize=0.75];');

  if (hasEntry) {
    lines.push(
      `  ${ENTRY} [label="", shape=circle, ${PSEUDO_COMMON}, style=filled, fillcolor=black, penwidth=0${entries ? markedDot(dotStatus(entries)) : ""}];`,
    );
    lines.push(`  { rank=min; ${ENTRY}; }`);
  }

  if (hasExit) {
    // Same width/height as ENTRY; black filled inner disc with double-circle UML final ring.
    lines.push(
      `  ${EXIT} [label="", shape=doublecircle, ${PSEUDO_COMMON}, style=filled, fillcolor=black, color=black, penwidth=0.9${exits ? markedDot(dotStatus(exits)) : ""}];`,
    );
    lines.push(`  { rank=max; ${EXIT}; }`);
  }

  for (const s of data.states) {
    if (s.diff) {
      lines.push(markedState(s.key, formatStateTitle(s.display_name, s.key), s.id, s.diff, paintByKinds ? paletteForStateType(s.state_type ?? "") : null));
      continue;
    }
    const id = dotQuoteId(s.key);
    const { fill, stroke } = paletteForStateType(s.state_type ?? "");
    const attributes = s.attributes ?? {};
    const nodeFill = dotColor(attributes.fill_color, fill);
    const nodeStroke = dotColor(attributes.color, stroke);
    const title = formatStateTitle(s.display_name, s.key);
    const label = `<<B>${htmlEscape(title)}</B>>`;
    lines.push(
      `  ${id} [label=${label}, shape=box, style="rounded,filled", fillcolor="${nodeFill}", color="${nodeStroke}", penwidth=1.15];`,
    );
  }

  if (entries) {
    for (const arrow of entries) lines.push(`  ${ENTRY} -> ${dotQuoteId(arrow.key)}${markedLine(arrow.diff, null)};`);
  } else {
    for (const ik of initialOk) {
      lines.push(`  ${ENTRY} -> ${dotQuoteId(ik)};`);
    }
  }

  const seen = new Set<string>();
  for (const t of data.transitions) {
    if (!stateKeys.has(t.source) || !stateKeys.has(t.target)) continue;
    const sig = `${t.source}\0${t.target}`;
    if (seen.has(sig)) continue;
    seen.add(sig);
    lines.push(`  ${dotQuoteId(t.source)} -> ${dotQuoteId(t.target)}${t.diff ? markedLine(t.diff, t.id) : ""};`);
  }

  if (exits) {
    for (const arrow of exits) lines.push(`  ${dotQuoteId(arrow.key)} -> ${EXIT}${markedLine(arrow.diff, null)};`);
  } else {
    for (const s of finals) {
      lines.push(`  ${dotQuoteId(s.key)} -> ${EXIT};`);
    }
  }

  lines.push("}");
  return lines.join("\n");
}
