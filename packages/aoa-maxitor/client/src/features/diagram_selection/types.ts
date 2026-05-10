// packages/aoa-maxitor/client/src/features/diagram_selection/types.ts
/** Sidebar-to-view contract for the currently selected diagram target. */
export type DiagramSelection =
  | { kind: "interchange_graph" }
  | { kind: "erd"; qualifier: string | null };
