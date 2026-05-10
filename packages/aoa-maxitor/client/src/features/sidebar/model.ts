// packages/aoa-maxitor/client/src/features/sidebar/model.ts
import { apiUrl } from "../../shared/config/api";
import type { DiagramSelection } from "../diagram-viewer";
import type { NodeRow, SidebarGroupedMaps, SidebarPayload } from "./types";

/** Client-side ERD uses JSON from ``/api/v1/erd/*``; interchange graph stays iframe HTML. */
export function diagramSelectionForRow(row: NodeRow): DiagramSelection | null {
  if (row.type === "graph") {
    return { kind: "iframe", url: apiUrl("/api/diagrams/graph") };
  }
  if (row.type === "erd_all") {
    return { kind: "erd", qualifier: null };
  }
  if (row.type === "erd_domain" && row.parent_id) {
    return { kind: "erd", qualifier: String(row.parent_id) };
  }
  return null;
}

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
