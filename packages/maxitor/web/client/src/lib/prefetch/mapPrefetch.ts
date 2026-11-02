// src/lib/prefetch/mapPrefetch.ts
/** Warm the map's engine when the user hovers the full graph in the panel (dynamic import only). */
export function prefetchMapEngine(): void {
  void import("@/components/diagrams/MapViewer/mapEngine");
}
