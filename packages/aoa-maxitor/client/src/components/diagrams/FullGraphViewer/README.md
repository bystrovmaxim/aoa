# FullGraphViewer


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** AntV G6 workspace for the full interchange topology (`GET /api/v1/full-graph`): loading, layout, legends, zoom toolbar.

## Public exports

**`index.ts`** exports **`FullGraphViewer`** only. Prefetch and fetch helpers live under **`@/lib/prefetch/g6Prefetch`** and **`@/api/fullGraph`**.

## Files

| File | Responsibility |
|------|----------------|
| `FullGraphViewer.tsx` | G6 mount lifecycle and viewport UX. |
| `layoutSettings.ts` | The d3-force settings and the layout version, in one place; the layout and the fingerprint both read them. |
| `forceLayout.ts` | The full graph's layout, the same on every engine and screen: origin centre, starting spiral, payload order; imported lazily with G6. |
| `initialPositions.ts` | The starting golden-angle spiral, computed without `Math.cos` / `Math.sin`. |
| `forceLayout.worker.ts` | Module worker around `forceLayout.ts`; kept as the record of spec 026, not used by the viewer. |
| `precomputedLayout.ts` | A G6 layout that returns given positions, so G6 draws them through its own pre-layout. |
| `arrangementStore.ts` | The fingerprint and the IndexedDB store of remembered arrangements, bounded to twenty. |
