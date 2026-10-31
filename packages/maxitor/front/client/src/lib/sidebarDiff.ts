// src/lib/sidebarDiff.ts
/**
 * The left panel of two versions (spec 038, FR-032; research R15): the pages of A and of B together, each once,
 * a page that only one of them has marked with the side it is in. A page is known by what it opens — its kind,
 * its node and the node it stands under — never by its label, which two different pages may share.
 */

import type { CompareResult } from "@/api/compare";
import type { NodeRow, SidebarPayload } from "@/model/sidebar";

/** A page's identity across two versions. */
export function pageKey(row: NodeRow): string {
  return `${row.type}|${row.id}|${row.parent_id ?? ""}`;
}

/** B's rows in B's order, then the rows only A has; a row in one only carries ``only``. */
function mergedRows(older: readonly NodeRow[], newer: readonly NodeRow[]): NodeRow[] {
  const before = new Set(older.map(pageKey));
  const now = new Set(newer.map(pageKey));
  return [
    ...newer.map((row) => (before.has(pageKey(row)) ? row : { ...row, only: "b" as const })),
    ...older.filter((row) => !now.has(pageKey(row))).map((row) => ({ ...row, only: "a" as const })),
  ];
}

/** The lifecycles with a state or a transition that differs; both ids begin with the lifecycle's id, a colon and the state. */
function changedLifecycles(compared: CompareResult): Set<string> {
  const lifecycles = new Set<string>();
  for (const id of [...Object.keys(compared.nodes), ...Object.keys(compared.edges)]) {
    const element = id.split("|")[0];
    lifecycles.add(element.slice(0, element.lastIndexOf(":")));
  }
  return lifecycles;
}

/** ``changed`` on a lifecycle's row that both versions have, when something in it differs (spec 042, FR-026a). */
function markChanged(rows: NodeRow[], compared: CompareResult | null): NodeRow[] {
  if (!compared) return rows;
  const lifecycles = changedLifecycles(compared);
  return rows.map((row) => (row.type === "lifecycle_state_diagram" && !row.only && lifecycles.has(row.id) ? { ...row, changed: true } : row));
}

/** The left panel of A and B merged: every page of either, ``only: "a"`` on A's alone, ``only: "b"`` on B's. */
export function mergeSidebars(older: SidebarPayload, newer: SidebarPayload, compared: CompareResult | null = null): SidebarPayload {
  return {
    ...newer,
    level1_nodes: mergedRows(older.level1_nodes, newer.level1_nodes),
    level2_diagrams: mergedRows(older.level2_diagrams, newer.level2_diagrams),
    level2_nodes: mergedRows(older.level2_nodes, newer.level2_nodes),
    level3_diagrams: markChanged(mergedRows(older.level3_diagrams, newer.level3_diagrams), compared),
  };
}
