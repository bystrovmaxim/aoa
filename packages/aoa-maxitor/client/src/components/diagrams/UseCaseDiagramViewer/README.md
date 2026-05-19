# UseCaseDiagramViewer

**Role:** Graphviz **dot** rendering of a domain **UML-style use-case** diagram (`GET` via **`@/api/domainUseCaseDiagram`**): WASM layout to SVG, **pan/zoom** via **`useSvgPanZoom`**, dotted canvas, **Fit to window** in **`ZoomToolbar`**, optional **boundary** subgraph, **dot LR/TB** plus **Neato/FDP** presets, optional **single-hop filtering**, and **`postProcessGraphvizSvgDom`** from **`@/lib/sanitizeGraphvizSvgOverlays`** so backdrop and edge arrow fills do not hide the grid.

## Public exports

**`index.ts`** exports **`UseCaseDiagramViewer`** and **`UseCaseDiagramViewerProps`**. DOT bundles are produced by **`@/lib/buildDomainUseCaseDotSource`**; domain narrowing uses **`@/lib/filterUseCaseDiagramByDomains`**; WASM prefetch uses **`@/lib/prefetch/erdGraphviz`**.

## Files

| File | Responsibility |
|------|----------------|
| `UseCaseDiagramViewer.tsx` | Fetch diagram JSON, legend and one-hop controls, rankdir/layout engine presets, DOT → SVG inject, viewport fit/center. |
