# DomainLegend

**Role:** Multi-domain ERD legend with visibility toggles in the Graphviz viewport. Row chrome matches `NodeTypeLegend` (shared `floatingLegend*` styles from `@/lib/ui`). Each row uses the shared Domain disk from `@/lib/icons` (`svgDataUriForInterchangeDomainLegend`) tinted with the domain accent; off rows are dimmed (opacity), no bordered chips.

## Files

| File | Responsibility |
|------|----------------|
| `DomainLegend.tsx` | Renders domain rows as lightweight toggle buttons. |
