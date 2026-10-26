# Contract: the layout worker

`FullGraphViewer/forceLayout.worker.ts` is a module worker. It takes one message, answers once and is then terminated by the viewer. The computation lives in `forceLayout.ts`, which only the worker and the unit tests import, so `@antv/layout` never enters the chunk every view loads. The main-thread fallback is today's path, G6's own layout with the same settings, which gives the same positions (research R4).

## Request (viewer → worker)

```ts
type LayoutRequest = {
  nodes: string[];                 // node ids, payload order
  edges: [string, string][];       // [source, target], payload order
  nodeVisualPx: number;            // payload.constants.node_visual_px
  width: number;                   // canvas width in CSS pixels at layout time
  height: number;                  // canvas height
};
```

Everything is structured-clonable: no function crosses the boundary. The settings are not sent; both sides import `layoutSettings.ts`.

## Response (worker → viewer)

```ts
type LayoutResponse =
  | { ok: true; positions: Record<string, [number, number]>; ms: number }
  | { ok: false; error: string };
```

## Behaviour

- The worker builds `D3ForceLayout` from `@antv/layout` with the options `initGraphLayout` in G6 5.1.1 would build from today's viewer (research R3), given as one explicit nested object — `center: {x: width/2, y: height/2, z: 0, strength: 0.012}`, distance 72 and strength 0.82 as constants, never a shallow spread that would lose `center.strength` (research R4) — calls `execute`, `stop`, `tick(220)` exactly as G6 does, and reads each node's `x`, `y`.
- **Fallback**: if the worker cannot be created, posts an error, answers `ok: false`, or answers with a result failing the data-model validation, the viewer logs `Full graph layout: the background layout is unavailable, laying out on the main thread.` once with `console.warn`, and builds the graph with G6's own `layout` option, set from `LAYOUT_SETTINGS` — today's path, whose code is already in the G6 chunk the page loaded — and remembers nothing from it (the next open tries the worker again). The measurement tool fails a run on this message (FR-003).
- **Cancellation**: when the viewer unmounts or the payload changes before the answer arrives, it calls `worker.terminate()`, and nothing is drawn or remembered (FR-013).
- **Equivalence**: for the same input, the worker's positions equal those of today's G6 configuration to 1e-9 (vitest, research R4).
