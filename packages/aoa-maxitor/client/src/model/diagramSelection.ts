// src/model/diagramSelection.ts
/** Sidebar-to-view contract for the currently selected diagram target. */
export type DiagramSelection =
  | { kind: "interchange_graph" }
  | { kind: "erd"; qualifier: string | null };
