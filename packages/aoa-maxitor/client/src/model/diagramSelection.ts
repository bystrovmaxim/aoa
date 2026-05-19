// src/model/diagramSelection.ts
/** Sidebar-to-view contract for the currently selected diagram target. */
export type DiagramSelection =
  | { kind: "interchange_graph" }
  | { kind: "erd"; qualifier: string | null }
  | { kind: "lifecycle_fsm"; lifecycle_graph_node_id: string; host_entity_interchange_id: string }
  | { kind: "use_case"; domain_qualifier: string };
