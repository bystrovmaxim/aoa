# Contract: identical layouts and the cross-engine step

## The full-graph layout (FR-001 … FR-004)

Module `client/src/components/diagrams/FullGraphViewer/forceLayout.ts`, imported lazily with G6.

```ts
computeForceLayout(request: { nodes: string[]; edges: [string, string][]; nodeVisualPx: number }):
  Record<string, [number, number]>
```

- **Input order** is the server's payload order; the function never sorts.
- **Starting positions** come from `initialPositions(nodeIds, radius)`: node *i* at radius `radius · sqrt(0.5 + i)`, angle advanced by multiplying the previous unit vector by the literal constants `GOLDEN_COS`, `GOLDEN_SIN`. Only `+ − × ÷` and `Math.sqrt`.
- **Centre** `{x: 0, y: 0, z: 0, strength: LAYOUT_SETTINGS.centerStrength}`; no width or height enters the layout.
- **Settings** all from `LAYOUT_SETTINGS`; `iterations` steps exactly, by `tick(iterations)` after `stop()`.
- **Forbidden during the layout**: `Math.cos`, `Math.sin`, `Math.pow`, `Math.random`.
- **Output** is drawn through `PrecomputedLayout`; G6's own layout is not used for the full graph.
- `LAYOUT_VERSION` (integer, `layoutSettings.ts`) is part of the arrangement fingerprint; it is raised by any change that can move a node.

## The layout hash (R9)

| Viewer | Hash |
|---|---|
| Full graph | `layoutHash(positions, nodeIds)`: SHA-256, hex, over `Float64Array` little-endian pairs `[x0, y0, x1, y1, …]` in payload order |
| ERD, use case, lifecycle | SHA-256, hex, of the SVG string `@hpcc-js/wasm-graphviz` returned for the page's DOT, before any post-pass |

Every viewer writes its hash as `data-layout-hash` on its diagram element once the picture is drawn, and clears it while a new layout runs.

## Tests in `npm test` (FR-005)

- **Guard**: `Math.cos`, `Math.sin`, `Math.pow`, `Math.random` are replaced by spies for the duration of `computeForceLayout` on the fixture; each must have zero calls. A second case checks that the layout request carries no width or height and that the same input gives the same hash whatever `window.innerWidth` and `innerHeight` are set to.
- **Golden**: the hash of the fixture's layout equals the constant written in the test.
- **Spiral**: `initialPositions` gives finite, distinct positions and equals a reference table for the first 16 nodes.

## The cross-engine step (FR-006)

`node scripts/check-layout-determinism.ts` in `packages/aoa-maxitor/client`, after `npm run build`.

1. Serve the built bundle and a stub Maxitor API answering from `packages/aoa-maxitor/tests/fixtures/ref-graph-2026-10-26.json.gz`.
2. For each engine in Chromium, Firefox, WebKit; each viewport in 375×812, 1600×900; each page of the fixture (the full graph, every domain's ERD, every domain's use-case diagram, every lifecycle) and each layout mode of that page: open it, wait for `data-layout-hash`, record it.
3. Print one line per page and mode: the hash, or every differing hash with its engine and size.
4. Exit `0` when, for every page and mode, all six hashes are equal; `1` otherwise.

Check-run step in `scripts/run_checks_with_log.sh`, after "Maxitor client: unit tests":

```bash
run_and_log "(cd packages/aoa-maxitor/client && npx playwright install chromium firefox webkit && node scripts/check-layout-determinism.ts)" "Maxitor client: the same layout in three engines"
```
