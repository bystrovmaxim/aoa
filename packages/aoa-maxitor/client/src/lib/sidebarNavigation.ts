// src/lib/sidebarNavigation.ts
import type { DiagramSelection } from "@/model/diagramSelection";
import type { NodeRow, SidebarGroupedMaps, SidebarPayload } from "@/model/sidebar";

/** ERD uses ``GET /api/v1/list-domains`` and ``GET /api/v1/list-entities``; interchange graph uses ``GET /api/v1/full-graph`` + G6 in the SPA. */
export function diagramSelectionForRow(row: NodeRow): DiagramSelection | null {
  if (row.type === "graph") {
    return { kind: "interchange_graph" };
  }
  if (row.type === "erd_all") {
    return { kind: "erd", qualifier: null };
  }
  if (row.type === "erd_domain" && row.parent_id) {
    return { kind: "erd", qualifier: String(row.parent_id) };
  }
  return null;
}

/**
 * Alphabetical order for nested rows (level-2+). Do **not** use for
 * ``level1_nodes``: the API returns roots in a fixed contract order
 * (``_ROOT_SECTIONS`` on the server); preserve that array order in the UI.
 */
export function sortNodes(nodes: NodeRow[]): NodeRow[] {
  return [...nodes].sort((a, b) => {
    const lc = a.label.toLowerCase().localeCompare(b.label.toLowerCase());
    if (lc !== 0) return lc;
    return a.id.localeCompare(b.id);
  });
}

export function buildSidebarGroupedMaps(sidebar: SidebarPayload): SidebarGroupedMaps {
  const l2ByParent = new Map<string, NodeRow[]>();
  for (const n of sidebar.level2_nodes) {
    const pk = n.parent_id ?? "";
    if (!l2ByParent.has(pk)) l2ByParent.set(pk, []);
    l2ByParent.get(pk)!.push(n);
  }
  const l3ByParent = new Map<string, NodeRow[]>();
  for (const n of sidebar.level3_diagrams) {
    const pk = n.parent_id ?? "";
    if (!l3ByParent.has(pk)) l3ByParent.set(pk, []);
    l3ByParent.get(pk)!.push(n);
  }
  const diagramsByParent = new Map<string, NodeRow[]>();
  for (const n of sidebar.level2_diagrams) {
    const pk = n.parent_id ?? "";
    if (!diagramsByParent.has(pk)) diagramsByParent.set(pk, []);
    diagramsByParent.get(pk)!.push(n);
  }
  return { l2ByParent, l3ByParent, diagramsByParent };
}
