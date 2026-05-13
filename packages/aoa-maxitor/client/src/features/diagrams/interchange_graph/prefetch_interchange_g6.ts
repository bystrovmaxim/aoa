// packages/aoa-maxitor/client/src/features/diagrams/interchange_graph/prefetch_interchange_g6.ts
/** Warm the G6 bundle when the user hovers interchange graph nav (dynamic import only). */
export function prefetchInterchangeG6(): void {
  void import("@antv/g6");
}
