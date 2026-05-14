# FullGraphViewer

**Role:** AntV G6 workspace for the full interchange topology (`GET /api/v1/full-graph`): loading, layout, legends, zoom toolbar.

## Public exports

**`index.ts`** exports **`FullGraphViewer`** only. Prefetch and fetch helpers live under **`@/lib/prefetch/g6Prefetch`** and **`@/api/fullGraph`**.

## Files

| File | Responsibility |
|------|----------------|
| `FullGraphViewer.tsx` | G6 mount lifecycle and viewport UX. |
