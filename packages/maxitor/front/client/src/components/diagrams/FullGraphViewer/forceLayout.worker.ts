// src/components/diagrams/FullGraphViewer/forceLayout.worker.ts
/**
 * The layout worker: one request in, one answer out, no state kept.
 *
 * It exists so the 220 steps of `d3-force` run off the main thread; G6 then only draws the
 * positions it is given (contracts/layout-worker.md).
 */

import { computeForceLayout } from "./forceLayout";
import type { LayoutRequest, LayoutResponse } from "./forceLayout";

type WorkerScope = {
  onmessage: ((event: MessageEvent<LayoutRequest>) => void) | null;
  postMessage: (message: LayoutResponse) => void;
};

const scope = self as unknown as WorkerScope;

scope.onmessage = (event) => {
  const started = performance.now();
  try {
    const positions = computeForceLayout(event.data);
    scope.postMessage({ ok: true, positions, ms: performance.now() - started });
  } catch (error) {
    scope.postMessage({ ok: false, error: error instanceof Error ? error.message : String(error) });
  }
};
