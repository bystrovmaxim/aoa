// packages/aoa-maxitor/client/src/features/diagrams/erd/hooks/use_graphviz.ts
/**
 * Lazy singleton load of ``@hpcc-js/wasm-graphviz`` — one module-level promise shared across remounts.
 */

import { Graphviz } from "@hpcc-js/wasm-graphviz";

let graphvizModule: Promise<Graphviz> | null = null;

/** Fire-and-forget WASM init so hovering the ERD nav warms the module before first paint. */
export function prefetchErdGraphviz(): void {
  void loadGraphvizWasm();
}

export function loadGraphvizWasm(): Promise<Graphviz> {
  if (!graphvizModule) {
    graphvizModule = Graphviz.load();
  }
  return graphvizModule;
}
