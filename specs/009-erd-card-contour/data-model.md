# Phase 1 — Data model: the drawing a card is made of

**Feature**: `specs/009-erd-card-contour` | **Date**: 2026-10-18

This feature stores no data. What it has is a **model of the drawing** — the shapes a table card is
composed of, as they arrive in the rendered markup — and the rules that decide how those shapes are
trimmed. The model below is the vocabulary of the implementation and of the check.

## What the renderer emits for one card

The shapes of one card live inside one node group. A real card, one header plus one field row:

```text
<g id="node1" class="node">
  <title>ShowcaseEntity</title>
  <path fill="white" stroke="none" d="M12,0C12,0 90.03,0 90.03,0 96.03,0 102.03,-6 102.03,-12 …"/>
  <polygon fill="#f5a623" stroke="none" points="1,-22.2 1,-44.6 101.03,-44.6 101.03,-22.2 1,-22.2"/>
  <text …>ShowcaseEntity</text>
  <polygon fill="#fef9c3" stroke="none" points="1,-1 1,-22.2 40.75,-22.2 40.75,-1 1,-1"/>
  <text …>PK</text>
  …
  <path fill="none" stroke="#f5a623" d="M12,0C12,0 90.03,0 …"/>
</g>
```

Two facts in that markup are the whole feature: the **contour** is a rounded rectangle, and each
**fill** is a plain rectangle that runs past the contour's corners.

## Entities

### Contour

The card's outline, read from the backdrop path.

| Attribute | Meaning | Derivation | Measured today |
|---|---|---|---|
| `x0`, `x1` | horizontal extent | min / max x among the path's coordinates | `0`, `102.03` |
| `y0`, `y1` | vertical extent | min / max y among the path's coordinates | `-45.6`, `0` |
| `radius` | corner radius | x of the path's first `M` command minus `x0` | `12` |

### Fill

One coloured rectangle inside the card: the header band, a primary-key tint, a foreign-key tint, a
body row. It is a polygon with four points; its colour and its row are not the feature's business.

| Attribute | Meaning | Derivation |
|---|---|---|
| `points` | the rectangle, as emitted | the polygon's `points` attribute |
| `fill` | the colour | the polygon's `fill` attribute |

### Inset

How far a fill is kept away from the contour by the renderer. It is measured, not assumed: the
smallest offset, on either axis, between any fill's edge and the contour's edge.

| Attribute | Derivation | Measured today |
|---|---|---|
| `inset` | `min(fill bounds) − min(contour bounds)` over all fills of the card | `1` |
| `inset radius` | `radius − inset`, never below 0 | `11` |

### Card (a node group that qualifies)

A node group is a card for the purposes of this feature when it holds a backdrop path with a real
arc (`radius > 0`) and at least one filled shape that is not that backdrop. A node group that
already carries a clip is not processed again.

### Clip

The trimming result, one per card: a `<clipPath>` element whose single child is a path describing
the contour shrunk by `inset` with radius `inset radius`, at the contour's corner centres. Every
fill of the card references it.

## Lexicon

One act, one mechanism, one word each — the feature uses them in this sense only:

| Word | What it names |
|---|---|
| **trim** | the act of bringing a fill inside the contour (FR-015) |
| **clip** | the mechanism that does it: a `<clipPath>` and the `clip-path` reference |
| **pass** | the whole step: `containNodeFills(svg)` |
| **inset** | the renderer's own distance between a fill and the contour — `1` today, measured, never assumed |

## Invariants the implementation must hold


| Id | Invariant | Requirement |
|---|---|---|
| I-1 | No fill lies outside the inset contour | FR-001, FR-015 |
| I-2 | No fill is painted under the stroke | FR-001, FR-015 |
| I-3 | The contour's radius, bounds and stroke are unchanged by the pass | FR-002 |
| I-4 | Fill colours and their row assignment are unchanged | FR-003 |
| I-5 | Text, edges, arrowheads and the canvas are byte-identical after the pass | FR-004, FR-005 |
| I-6 | A node group that is not a card is returned byte-identical | FR-010 |
| I-7 | A card with a single fill is clipped on all four corners | US1-4 |
| I-8 | The pass is pure and idempotent | FR-011, R5 |
| I-9 | One clip per card, one attribute per fill — the work is linear | FR-016, R9 |
| I-10 | The pass is **additive**: remove the clip elements it inserted and the attributes it set, and the markup is byte-identical to its input | FR-002, FR-003, FR-004, FR-005 |

## Validation rules

- **V-1** — the geometry is derived from the markup (R3); a constant for `radius` or `inset` in the
  code is a defect.
- **V-2** — `inset` is at least `0` and smaller than half the smaller side of the contour; a card
  narrower than twice the radius still yields a clip, with `inset radius` clamped at `0` (spec edge
  case).
- **V-3** — a clip id is unique per card and deterministic: `erd-fill-clip-<node group id>`.
- **V-4** — a group already carrying a clip is skipped (idempotence, I-8).
- **V-5** — the pass never throws on markup it does not recognise; it returns its input unchanged.
  An unparsable card is a card left as it was, never a failed diagram.

## What is deliberately not modelled

Edges, arrowheads, edge labels, the dashed cluster frame, the dotted canvas, the legend, the
toolbar and the empty state. They are outside the feature and are asserted only as unchanged
(FR-005, FR-010).
