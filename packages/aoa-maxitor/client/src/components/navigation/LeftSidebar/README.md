# LeftSidebar

**Role:** Left navigation tree — **`useSidebarPayload`** runs inside **`LeftSidebar`** only (§2.3); parents pass **`diagram`** / **`onSelectDiagram`**; rows prefetch G6 / Graphviz WASM on hover.

## Files

| File | Responsibility |
|------|----------------|
| `LeftSidebar.tsx` | Sidebar fetch + grouping + list UI + selection callbacks. |
| `hooks/useSidebarPayload.ts` | Fetches `/api/sidebar` via `@/api/sidebar` (not exported from **`index.ts`**). |
| `SidebarRowIcon.tsx` | Row-type icon — private helper colocated here (§1), not a separate component root. |
