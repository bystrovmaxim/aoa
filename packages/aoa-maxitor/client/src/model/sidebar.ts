// src/model/sidebar.ts
export type NodeRow = {
  id: string;
  parent_id: string | null;
  label: string;
  type: string;
  /** Lower sorts earlier among siblings; omit for label-only sort (e.g. level-2 nodes). */
  ordinal?: number;
};

export type SidebarPayload = {
  level1_nodes: NodeRow[];
  level2_diagrams: NodeRow[];
  level2_nodes: NodeRow[];
  level3_diagrams: NodeRow[];
};

export type SidebarGroupedMaps = {
  l2ByParent: Map<string, NodeRow[]>;
  l3ByParent: Map<string, NodeRow[]>;
  diagramsByParent: Map<string, NodeRow[]>;
};
