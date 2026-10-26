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
| `layoutSettings.ts` | The d3-force settings that are in effect today, in one object; the fallback's G6 options and the fingerprint both read it. |
| `forceLayout.ts` | The layout run the way G6 runs it (`execute`, `stop`, `tick`); imported by the worker and the tests only, never by the viewer. |
| `forceLayout.worker.ts` | Module worker: one request in, one answer out, no state kept. |
