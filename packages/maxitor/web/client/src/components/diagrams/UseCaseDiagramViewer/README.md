# UseCaseDiagramViewer


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Graphviz **dot** rendering of a domain **UML-style use-case** diagram (`GET` via **`@/api/domainUseCaseDiagram`**): WASM layout to SVG, **pan/zoom** via **`useSvgPanZoom`**, dotted canvas, **Fit to window** in **`ZoomToolbar`**, optional **boundary** subgraph, **dot LR/TB** plus **Neato/FDP** presets, optional **single-hop filtering**, and **`postProcessGraphvizSvgDom`** from **`@/lib/sanitizeGraphvizSvgOverlays`** so backdrop and edge arrow fills do not hide the grid. In Diff it draws A and B together: each action, role and link marked, an action changed inside marked as changed, everything else faded; the counts go to the version button; a click opens the card, and the stepper walks the changes. The filter panel holds Domains and, in Diff, Changes, with the paint switch (spec 041).

## Public exports

**`index.ts`** exports **`UseCaseDiagramViewer`** and **`UseCaseDiagramViewerProps`**. DOT bundles are produced by **`@/lib/buildDomainUseCaseDotSource`**; domain narrowing uses **`@/lib/filterUseCaseDiagramByDomains`**; WASM prefetch uses **`@/lib/prefetch/erdGraphviz`**.

## Files

| File | Responsibility |
|------|----------------|
| `UseCaseDiagramViewer.tsx` | Fetch diagram JSON, legend and one-hop controls, rankdir/layout engine presets, DOT → SVG inject, viewport fit/center. |
