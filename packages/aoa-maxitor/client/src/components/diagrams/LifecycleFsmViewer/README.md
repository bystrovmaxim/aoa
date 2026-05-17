# LifecycleFsmViewer

**Role:** Graphviz **dot** rendering of an entity **lifecycle finite automaton** (`GET /api/v1/lifecycle-finite-automaton`): WASM layout to SVG, pan/zoom via **`useSvgPanZoom`**, LR/TB rank direction, dotted canvas, and **Fit to window** in **`ZoomToolbar`**.

## Public exports

**`index.ts`** exports **`LifecycleFsmViewer`** and **`LifecycleFsmViewerProps`**. DOT text is built in **`@/lib/buildLifecycleFsmDotSource`**; WASM prefetch uses **`@/lib/prefetch/erdGraphviz`**.

## Files

| File | Responsibility |
|------|----------------|
| `LifecycleFsmViewer.tsx` | Load automaton JSON, build DOT, layout SVG, fit/center viewport, rankdir toggle, error surface. |
