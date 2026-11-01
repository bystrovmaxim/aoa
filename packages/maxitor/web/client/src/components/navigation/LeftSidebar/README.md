# LeftSidebar


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Left navigation tree — **`useSidebarPayload`** runs inside **`LeftSidebar`** only (§2.3); parents pass **`diagram`** / **`onSelectDiagram`**; rows prefetch the map engine / Graphviz WASM on hover. In Diff (spec 038, FR-032) it lists the pages of A and B together, `+` on a page only B has and `−` on one only A has.

While a source is open the header shows **`ReloadServiceButton`** ("Reload from service"): one click sends one `POST /api/load` for the current source, the sidebar is read again and the diagram workspace is remounted; the URL and the selected diagram stay. The button is disabled while the reload runs, and a failed reload is reported in the footer without clearing the diagram. A busy server is reported there too, while the page waits and retries its reads.

## Files

| File | Responsibility |
|------|----------------|
| `LeftSidebar.tsx` | Sidebar fetch + grouping + list UI + selection callbacks. |
| `hooks/useSidebarPayload.ts` | Fetches `/api/sidebar` via `@/api/sidebar` (not exported from **`index.ts`**); in Diff also A's, merged by `@/lib/sidebarDiff`. |
| `SidebarRowIcon.tsx` | Row-type icon — private helper colocated here (§1), not a separate component root. |
| `ReloadServiceButton.tsx` | "Reload from service" control for the open source; disabled while its reload runs. |
| `ProjectFooter.tsx` | The bottom of the panel: the GitHub mark linking to the project, **Maxitor** and the running version from `/api/meta/app-info` (never written into the client), centred; on the collapsed rail only the mark, with the tooltip "Maxitor on GitHub" (spec 028, FR-100 … FR-102). |
