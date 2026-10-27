// src/rooms/pageKey.ts
import type { DiagramSelection } from "@/model/diagramSelection";
import type { SidebarPayload } from "@/model/sidebar";
import { deepLinkToSelection, selectionToParams } from "@/lib/urlState";

/**
 * The canonical key of a page: its address parameters in the fixed order ``view``, ``domain``,
 * ``node``, ``host`` — the same key the room server builds from the left panel (``pages.py``).
 */
export function pageKeyOf(selection: DiagramSelection): string {
  return new URLSearchParams(selectionToParams(selection)).toString();
}

/** The page a key names, or ``null`` when it names none. */
export function selectionOfPageKey(key: string): DiagramSelection | null {
  const params = new URLSearchParams(key);
  return deepLinkToSelection({
    source: null,
    view: params.get("view"),
    domain: params.get("domain"),
    node: params.get("node"),
    host: params.get("host"),
    room: null,
  });
}

/** Every row of the left panel by id, for the names a page key carries only as ids. */
function labelOf(sidebar: SidebarPayload | null, id: string): string {
  if (!sidebar) return id;
  const rows = [...sidebar.level1_nodes, ...sidebar.level2_nodes, ...sidebar.level2_diagrams, ...sidebar.level3_diagrams];
  return rows.find((row) => row.id === id)?.label ?? id;
}

/** A page in words, as a circle's card and the join dialog show it: *ERD · all domains*. */
export function pageLabel(key: string | null, sidebar: SidebarPayload | null): string {
  const selection = key ? selectionOfPageKey(key) : null;
  if (!selection) return "No page yet";
  switch (selection.kind) {
    case "interchange_graph":
      return "Full graph";
    case "erd":
      return selection.qualifier ? `ERD · ${labelOf(sidebar, selection.qualifier)}` : "ERD · all domains";
    case "use_case":
      return `Use case · ${labelOf(sidebar, selection.domain_qualifier)}`;
    case "lifecycle_fsm":
      return `Lifecycle · ${labelOf(sidebar, selection.lifecycle_graph_node_id)}`;
  }
}
