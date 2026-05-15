// src/model/fullGraph.ts

/**
 * Interchange G6 payload types for ``GET /api/v1/full-graph``.
 *
 * **Contract (slim viewer, plan 019 / FullGraphAction):**
 * - `nodes[].data`: `label`, `title`, `node_type`, `fill` only.
 * - `edges[].data`: `label` (DuckDB `edges.relationship`), `edge_type` only.
 * - `constants` may include `layout_entity_scalar_link`, `entity_field_*` for Entity ↔ EntityField layout.
 * Do not add DuckDB `payload` blobs or duplicate id/relationship fields without updating
 * `tests/maxitor/`.
 *
 * **Wire metrics (PR-3):** run `uv run python scripts/measure_full_graph_payload.py` from repo root.
 */

/** Node ``data`` from ``GET /api/v1/full-graph`` (slim contract; G6 still types ``data`` as unknown). */
export type InterchangeGraphNodeData = {
  label: string;
  title: string;
  node_type: string;
  fill: string;
};

/** Edge ``data`` from ``GET /api/v1/full-graph``; ``label`` mirrors DuckDB ``edges.relationship``. */
export type InterchangeGraphEdgeData = {
  label: string;
  edge_type: string;
};

/** G6-oriented payload from ``GET /api/v1/full-graph`` (``body.payload``). */
export type InterchangeGraphG6Payload = {
  title: string;
  nodes: Array<{
    id: string;
    data?: InterchangeGraphNodeData;
    style?: { x?: number; y?: number; [k: string]: unknown };
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    data?: InterchangeGraphEdgeData;
  }>;
  legend_items: Array<{ type: string; color: string }>;
  node_type_map: Record<string, string>;
  domain_color_map?: Record<string, string>;
  bubble_plugins: Array<Record<string, unknown>>;
  constants: {
    node_visual_px: number;
    dag_cycle_violation_color: string;
    default_color: string;
    g6_cdn_url: string;
    /** Optional: d3-force tuning for ``Entity`` ↔ ``EntityField`` links (full graph). */
    layout_entity_scalar_link?: { distance: number; strength: number };
    entity_field_duck_slug?: string;
    entity_field_interchange_type?: string;
  };
};
