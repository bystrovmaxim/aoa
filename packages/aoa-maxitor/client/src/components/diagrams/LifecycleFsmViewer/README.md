# LifecycleFsmViewer


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Graphviz **dot** rendering of an entity **lifecycle finite automaton** (`GET /api/v1/lifecycle-finite-automaton`): WASM layout to SVG, pan/zoom via **`useSvgPanZoom`**, LR/TB rank direction, dotted canvas, and **Fit to window** in **`ZoomToolbar`**.

## Public exports

**`index.ts`** exports **`LifecycleFsmViewer`** and **`LifecycleFsmViewerProps`**. DOT text is built in **`@/lib/buildLifecycleFsmDotSource`**; WASM prefetch uses **`@/lib/prefetch/erdGraphviz`**.

## Files

| File | Responsibility |
|------|----------------|
| `LifecycleFsmViewer.tsx` | Load automaton JSON, build DOT, layout SVG, fit/center viewport, rankdir toggle, error surface. |
