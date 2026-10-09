# ErdViewer


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Full-page ERD workspace: loads domain bundles, renders **`parts/ErdGraphvizCanvas`** inside **`DiagramShell`**.

## Composition

- **`ErdViewer.tsx`** — selection + one-hop state + loader.
- **`parts/ErdGraphvizCanvas/`** — WASM Graphviz canvas.
- **`hooks/`** — `useGraphviz` (re-export to WASM singleton), `useSvgPanZoom`.

## Public exports

The folder **`index.ts`** exports **`ErdViewer`**, **`ErdViewerSelection`**, and **`ErdGraphvizCanvas`** (the canvas re-export is **only for isolated tests** of the Graphviz surface — app code should import **`ErdViewer`**). For **`listEntities`** / **`listDomains`**, **`buildDotSource`**, **`DomainLegend`**, etc., import from **`@/api/*`**, **`@/lib/*`**, **`@/components/ui/*`** — avoid a deep feature barrel (plan §7).

## Files

| File | Responsibility |
|------|----------------|
| `ErdViewer.tsx` | Shell + bundle loading. |
| `parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx` | DOT layout + SVG viewport. |
| `hooks/useGraphviz.ts` | Re-export `loadGraphvizWasm` / types from `@/lib/prefetch/erdGraphviz`. |
| `hooks/useSvgPanZoom.ts` | Pointer/wheel zoom helpers for SVG viewport. |
