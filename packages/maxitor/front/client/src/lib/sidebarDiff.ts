// src/lib/sidebarDiff.ts
/**
 * The left panel of two versions (spec 038, FR-032; research R15): the pages of A and of B together, each once,
 * a page that only one of them has marked with the side it is in. A page is known by what it opens — its kind,
 * its node and the node it stands under — never by its label, which two different pages may share.
 */

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

/** The left panel of A and B merged: every page of either, ``only: "a"`` on A's alone, ``only: "b"`` on B's. */
export function mergeSidebars(older: SidebarPayload, newer: SidebarPayload): SidebarPayload {
  return {
    ...newer,
    level1_nodes: mergedRows(older.level1_nodes, newer.level1_nodes),
    level2_diagrams: mergedRows(older.level2_diagrams, newer.level2_diagrams),
    level2_nodes: mergedRows(older.level2_nodes, newer.level2_nodes),
    level3_diagrams: mergedRows(older.level3_diagrams, newer.level3_diagrams),
  };
}
