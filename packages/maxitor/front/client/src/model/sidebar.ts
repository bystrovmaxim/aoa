// src/model/sidebar.ts
export type NodeRow = {
  id: string;
  parent_id: string | null;
  label: string;
  type: string;
  /** Lower sorts earlier among siblings; omit for label-only sort (e.g. level-2 nodes). */
  ordinal?: number;
  /** In Diff (spec 038): the page exists only in A, or only in B. */
  only?: "a" | "b";
};

export type SidebarPayload = {
  level1_nodes: NodeRow[];
  level2_diagrams: NodeRow[];
  level2_nodes: NodeRow[];
  level3_diagrams: NodeRow[];
  /** SHA-256 of the graph-json the panel was read from; a tab in a room reports it with its picture. */
  fingerprint?: string;
};

export type SidebarGroupedMaps = {
  l2ByParent: Map<string, NodeRow[]>;
  l3ByParent: Map<string, NodeRow[]>;
  diagramsByParent: Map<string, NodeRow[]>;
};
