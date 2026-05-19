# Maxitor lifecycle FSM (Graphviz SVG): auto-fit failures and fixes

**Status:** Accepted (implemented in `packages/aoa-maxitor/client`)  
**Date:** 2026-05-17

## Context

The Maxitor React SPA renders entity **lifecycle** diagrams as Graphviz-generated SVG inside a pan/zoom viewport (`LifecycleFsmViewer`, shared `useSvgPanZoom` with the ERD canvas). Operators expect the same behavior as the **Fit to window** control without clicking it: correct scale and centering after first paint, after window resize, and when toggling Graphviz **rank direction** (LR ↔ TB).

## Symptoms

1. **Manual fit worked; automatic fit did not** — clicking **Fit to window** produced a perfect frame, while the initial / automatic path left the graph clipped, off-center, or at the wrong zoom.
2. **Rankdir toggles were worse** — switching LR/TB reproduced bad fits until the user hit fit again.
3. **Jitter** — multiple back-to-back fits or showing an intermediate “wrong” frame before the final transform felt like the diagram was snapping.

## Root causes

1. **`visibility: hidden` during measurement** — Hiding the panner to avoid flashing a wrong frame caused `getBoundingClientRect()` on nested SVG groups to collapse to empty/zero boxes in some engines. `fitToContainer` then exited early (`!box`), leaving the default transform until a later manual fit (with visible content).
2. **Stale SVG while DOT recomputes** — On rankdir change, the **previous** SVG often stayed mounted until the async WASM `layout()` promise resolved. `ResizeObserver` and intermediate fit passes could measure **old geometry** while the new DOT string was already active, then `hasFittedRef` could mark a “successful” fit against the wrong content.
3. **`hasFittedRef` not aligned with real success** — The resize path called the inner fit implementation without reliably recording “we have a valid fit for the current SVG,” which made follow-up resize/refit logic easier to confuse during transitions.
4. **Bounding box choice** — Using only `g.graph` client rect could over-include invisible spline control hulls for some layouts, shrinking the computed scale; preferring a union of `g.node` / `g.edge` rects (with fallback) yields a tighter box for lifecycle graphs.
5. **One-frame layout drift** — After rankdir switches, text metrics / flex layout can shift slightly on the next frame; a single rAF chain sometimes matched what the user saw after clicking fit one frame later.

## Decisions / mitigations

1. **Hide pre-fit UI with `opacity: 0` + `pointer-events: none`**, not `visibility: hidden`, so layout and client rects remain measurable while avoiding a visible wrong frame.
2. **On every DOT change** (including LR ↔ TB), **clear `svgMarkup` synchronously** (after the first real diagram) so nothing measures or fits stale Graphviz output while the new SVG is pending.
3. **Set `hasFittedRef` only after a fit that computed a real `box` and applied the transform** (successful path inside `fitToContainer`), so “fitted” means fitted, not “ran but bailed early.”
4. **Keep `fitBottomInset`** for the floating zoom/rankdir toolbar so vertical centering does not tuck the graph under controls.
5. **Scheduling** — Retain a short **rAF chain** before the first fit; add **one follow-up `requestAnimationFrame`** pass (still while `opacity: 0`) to absorb post-rankdir layout drift without `setTimeout` jitter.

## Consequences

- Slightly more blank time (empty canvas) on rankdir switch while WASM runs; correctness beats showing the wrong diagram at the wrong zoom.
- ERD and lifecycle share `useSvgPanZoom`; lifecycle-specific sequencing lives in `LifecycleFsmViewer.tsx`.

## References

- `packages/aoa-maxitor/client/src/components/diagrams/LifecycleFsmViewer/LifecycleFsmViewer.tsx`
- `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/hooks/useSvgPanZoom.ts`
