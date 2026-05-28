# LeftSidebar


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Left navigation tree — **`useSidebarPayload`** runs inside **`LeftSidebar`** only (§2.3); parents pass **`diagram`** / **`onSelectDiagram`**; rows prefetch G6 / Graphviz WASM on hover.

## Files

| File | Responsibility |
|------|----------------|
| `LeftSidebar.tsx` | Sidebar fetch + grouping + list UI + selection callbacks. |
| `hooks/useSidebarPayload.ts` | Fetches `/api/sidebar` via `@/api/sidebar` (not exported from **`index.ts`**). |
| `SidebarRowIcon.tsx` | Row-type icon — private helper colocated here (§1), not a separate component root. |
