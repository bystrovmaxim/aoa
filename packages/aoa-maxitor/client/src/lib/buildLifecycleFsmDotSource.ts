// src/lib/buildLifecycleFsmDotSource.ts
import type { LifecycleFiniteAutomatonPayload } from "@/model/lifecycleFiniteAutomaton";

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

function paletteForStateType(t: string): { fill: string; stroke: string } {
  if (t === "initial") return { fill: "#ecfdf5", stroke: "#059669" };
  if (t === "final") return { fill: "#f8fafc", stroke: "#64748b" };
  return { fill: "#eff6ff", stroke: "#2563eb" };
}

export type LifecycleFsmRankdir = "LR" | "TB";

/** DOT source for Graphviz ``dot`` layout (UML-style entry / exit pseudostates). */
export function buildLifecycleFsmDotSource(data: LifecycleFiniteAutomatonPayload, rankdir: LifecycleFsmRankdir = "LR"): string {
  const stateKeys = new Set(data.states.map((s) => s.key));
  const initialOk = data.initial_state_keys.filter((k) => stateKeys.has(k));
  const finals = data.states.filter((s) => (s.state_type ?? "") === "final" && stateKeys.has(s.key));

  const lines: string[] = [];
  lines.push("digraph lifecycle_fsm {");
  lines.push(
    `  graph [rankdir=${rankdir}, bgcolor=transparent, splines=true, nodesep=0.45, ranksep=0.65, fontname="Helvetica Neue"];`,
  );
  lines.push('  node [fontname="Helvetica Neue", fontsize=11];');
  lines.push('  edge [color="#64748b", arrowsize=0.75];');

  if (initialOk.length > 0) {
    lines.push(
      `  ${ENTRY} [label="", shape=circle, ${PSEUDO_COMMON}, style=filled, fillcolor=black, penwidth=0];`,
    );
    lines.push(`  { rank=min; ${ENTRY}; }`);
  }

  if (finals.length > 0) {
    // Same width/height as ENTRY; black filled inner disc with double-circle UML final ring.
    lines.push(
      `  ${EXIT} [label="", shape=doublecircle, ${PSEUDO_COMMON}, style=filled, fillcolor=black, color=black, penwidth=0.9];`,
    );
    lines.push(`  { rank=max; ${EXIT}; }`);
  }

  for (const s of data.states) {
    const id = dotQuoteId(s.key);
    const { fill, stroke } = paletteForStateType(s.state_type ?? "");
    const title = formatStateTitle(s.display_name, s.key);
    const label = `<<B>${htmlEscape(title)}</B>>`;
    lines.push(
      `  ${id} [label=${label}, shape=box, style="rounded,filled", fillcolor="${fill}", color="${stroke}", penwidth=1.15];`,
    );
  }

  for (const ik of initialOk) {
    lines.push(`  ${ENTRY} -> ${dotQuoteId(ik)};`);
  }

  const seen = new Set<string>();
  for (const t of data.transitions) {
    if (!stateKeys.has(t.source) || !stateKeys.has(t.target)) continue;
    const sig = `${t.source}\0${t.target}`;
    if (seen.has(sig)) continue;
    seen.add(sig);
    lines.push(`  ${dotQuoteId(t.source)} -> ${dotQuoteId(t.target)};`);
  }

  for (const s of finals) {
    lines.push(`  ${dotQuoteId(s.key)} -> ${EXIT};`);
  }

  lines.push("}");
  return lines.join("\n");
}
