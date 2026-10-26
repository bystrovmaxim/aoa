# ErdFilterPanel


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** The ERD's one filter panel. Two sections, **Domains** and **Kinds**, behave as a strict accordion: exactly one is open at a time (Domains when the diagram mounts), opening one folds the other, and clicking the open header folds it. Rows use the same chrome as `DomainLegend` (shared `floatingLegend*` styles from `@/lib/ui`): a 20 px disk and a label, dimmed when switched off.

- **Width:** fixed at 148 px (`ERD_FILTER_PANEL_WIDTH`, the width the production Domains legend had); the panel never widens. A label that does not fit is cut with an ellipsis and shows its full text in a tooltip — only when it was actually cut.
- **Height:** the panel ends above the zoom toolbar and scrolls inside itself; wheel events stop at the panel, so scrolling it never zooms or pans the canvas.
- **Kinds:** the section is rendered only when the graph has more than one kind. Rows come from `GET /api/v1/list-entity-kinds`, labelled with the kind's display name.
- **Narrow screens:** the panel starts as a "Filter" pill; opened, it shows the sections straight away — the word "Filter" does not appear inside — with the close button at the end of the Domains header.

## Props

| Prop | Meaning |
|------|---------|
| `domainRows` | `ErdFilterRow[]` — one row per domain (or 1-hop qualifier): `key`, `label`, `iconSrc`, `on`. |
| `kindRows` | `ErdFilterRow[]` — one row per entity kind present in the graph. |
| `onToggleDomain` | Called with a domain row's `key` when it is clicked. |
| `onToggleKind` | Called with a kind row's `key` when it is clicked. |

## Files

| File | Responsibility |
|------|----------------|
| `ErdFilterPanel.tsx` | The panel, its accordion sections, the rows and the cut-only tooltip. |
| `ErdFilterPanel.test.tsx` | Width, accordion, tooltip, Kinds visibility, the mobile pill and wheel isolation. |
