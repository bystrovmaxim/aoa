# CollapsibleLegendPanel


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Shared floating legend chrome for `DomainLegend` and `NodeTypeLegend`. Desktop renders an always-expanded `aside` panel (`floatingLegendPanelSx`/`floatingLegendTitleSx` from `@/lib/ui`) with a `title` and arbitrary `children`; below the MUI `sm` breakpoint it starts collapsed to a small top-left pill (tap to expand), gaining a close button to collapse it back — a pinned full-height panel would otherwise cover most of a ~375px canvas.

## Files

| File | Responsibility |
|------|----------------|
| `CollapsibleLegendPanel.tsx` | Desktop/mobile chrome switch and collapse-state toggle. |
