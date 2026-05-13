// packages/aoa-maxitor/client/src/features/diagrams/interchange_graph/types.ts

/** G6-oriented payload from ``GET /api/v1/full-graph`` (``body.payload``). */
export type InterchangeGraphG6Payload = {
  title: string;
  nodes: Array<{
    id: string;
    data?: Record<string, unknown>;
    style?: { x?: number; y?: number; [k: string]: unknown };
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    data?: Record<string, unknown>;
  }>;
  legend_items: Array<{ type: string; color: string }>;
  node_type_map: Record<string, string>;
  bubble_plugins: Array<Record<string, unknown>>;
  constants: {
    node_visual_px: number;
    dag_cycle_violation_color: string;
    default_color: string;
    g6_cdn_url: string;
  };
};
