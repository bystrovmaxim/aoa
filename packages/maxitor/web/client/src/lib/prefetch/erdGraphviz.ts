// src/lib/prefetch/erdGraphviz.ts
/**
 * Lazy singleton load of ``@hpcc-js/wasm-graphviz`` — one module-level promise shared across remounts.
 * Lives under ``lib/prefetch`` so navigation can warm WASM without importing viewer hooks.
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

/**
 * The instance to lay out with ``engine``: a fresh one for FDP, the shared one for every other.
 *
 * FDP in this WebAssembly build reads state that earlier layouts leave in the instance, so the
 * same DOT laid out after a Neato or Dot run in the same page gives a different picture than in a
 * fresh page — and pointers in a room would land on different spots (spec 028, FR-006). Starting
 * FDP from a newly instantiated module gives the same picture every time.
 */
export function loadGraphvizWasmFor(engine: string): Promise<Graphviz> {
  if (engine !== "fdp") return loadGraphvizWasm();
  Graphviz.unload();
  graphvizModule = Graphviz.load();
  return graphvizModule;
}
