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
  if (row.type === "lifecycle_state_diagram" && row.parent_id) {
    return {
      kind: "lifecycle_fsm",
      lifecycle_graph_node_id: row.id,
      host_entity_interchange_id: String(row.parent_id),
    };
  }
  if (row.type === "use_case_domain" && row.parent_id) {
    return { kind: "use_case", domain_qualifier: String(row.parent_id) };
  }
  return null;
}

/**
 * Alphabetical order for nested rows (level-2+). Do **not** use for
 * ``level1_nodes``: the API returns roots in a fixed contract order
 * (``_ROOT_SECTIONS`` on the server); preserve that array order in the UI.
 * When ``ordinal`` is set, it sorts before label (lower first); rows without
 * ``ordinal`` sort after all ordinals, then by label.
 */
export function sortNodes(nodes: NodeRow[]): NodeRow[] {
  const rank = (n: NodeRow) => (typeof n.ordinal === "number" ? n.ordinal : Number.MAX_SAFE_INTEGER);
  return [...nodes].sort((a, b) => {
    const ra = rank(a);
    const rb = rank(b);
    if (ra !== rb) return ra - rb;
    const lc = a.label.toLowerCase().localeCompare(b.label.toLowerCase());
    if (lc !== 0) return lc;
    return a.id.localeCompare(b.id);
  });
}

/** First selectable row of the given kind, in sidebar order — resolves a ``view=`` deep link that didn't pin an exact qualifier. */
export function firstSelectionOfKind(sidebar: SidebarPayload, kind: DiagramSelection["kind"]): DiagramSelection | null {
  for (const row of sortNodes([...sidebar.level2_diagrams, ...sidebar.level3_diagrams])) {
    const sel = diagramSelectionForRow(row);
    if (sel?.kind === kind) return sel;
  }
  return null;
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
