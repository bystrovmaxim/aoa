# Contract — the containment pass

**Module**: `packages/aoa-maxitor/client/src/lib/containNodeFills.ts` (new)
**Consumer**: `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx`
**Date**: 2026-10-18

This is the interface contract, not the implementation. The shape of the code is decided at
implementation time; the promises below are what the check and the page rely on.

## Signature

```ts
export function containNodeFills(svg: string): string;
```

One argument: the markup `gv.layout(dot, "svg", engine)` returned. One return value: markup ready to
be injected into the page.

## Promises

1. **Total.** It never throws. Markup it does not recognise is returned unchanged (V-5).
2. **Pure.** The same input always yields the same output; it reads no globals and mutates no
   argument.
3. **Idempotent.** `containNodeFills(containNodeFills(x)) === containNodeFills(x)` (I-8, V-4).
4. **Selective.** A node group that is not a card — no rounded backdrop, or no fill besides it — is
   returned byte-identical (I-6, R4). This is what keeps the lifecycle and use-case drawings out of
   the change, and it is checked directly.
5. **Contained.** In every card that is processed, each fill references a clip whose path is the
   contour shrunk by the measured `inset`, with radius `radius − inset` and the contour's corner
   centres (I-1, I-2, R3).
6. **Conservative.** Nothing else in the markup changes: the contour path, the stroke, the fill
   colours, the text, the edges and the canvas keep their bytes (I-3, I-4, I-5).
7. **Deterministic naming.** Every clip carries `erd-fill-clip-<node group id>`; no counters, no
   timestamps, no randomness (V-3).
8. **Additive.** The only difference between output and input is what the pass inserted: one
   `<clipPath>` element per processed card and one `clip-path` attribute per fill. Strip those and the
   markup is byte-identical to the input — which is how the check proves that the contour, the
   colours, the text, the edges and the canvas are untouched (I-10, A-9).
9. **Linear.** One walk over the markup, one clip and one attribute per card; nothing is re-parsed
   per row (I-9, R9).

## Non-goals

- It does not decide which diagram is drawn; it is called by the ERD canvas only (R1).
- It does not touch the DOM; the existing DOM post-pass keeps its own job (`postProcessGraphvizSvgDom`).
- It does not repair a drawing whose contour is not a rounded rectangle.

## Where it is called

`ErdGraphvizCanvas`, in the effect that renders the layout: the string produced by `gv.layout(...)`
is passed through `containNodeFills` before it becomes the markup that is injected. Nothing else in
the client calls it.
