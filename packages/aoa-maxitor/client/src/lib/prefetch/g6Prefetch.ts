// src/lib/prefetch/g6Prefetch.ts
/** Warm the G6 bundle when the user hovers interchange graph nav (dynamic import only). */
export function prefetchInterchangeG6(): void {
  void import("@antv/g6");
}
