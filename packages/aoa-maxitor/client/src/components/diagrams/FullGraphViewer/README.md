# FullGraphViewer


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
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
