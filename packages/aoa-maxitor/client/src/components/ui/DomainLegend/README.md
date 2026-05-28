# DomainLegend


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Multi-domain ERD legend with visibility toggles in the Graphviz viewport. Row chrome matches `NodeTypeLegend` (shared `floatingLegend*` styles from `@/lib/ui`). Each row uses the shared Domain disk from `@/lib/icons` (`svgDataUriForInterchangeDomainLegend`) tinted with the domain accent; off rows are dimmed (opacity), no bordered chips.

## Files

| File | Responsibility |
|------|----------------|
| `DomainLegend.tsx` | Renders domain rows as lightweight toggle buttons. |
