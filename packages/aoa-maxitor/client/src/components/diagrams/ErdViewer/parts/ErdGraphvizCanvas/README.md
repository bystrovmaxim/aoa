# ErdGraphvizCanvas


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Graphviz WASM render surface for merged ERD domain payloads: layout presets, pan/zoom, domain legend and neighborhood toggle composed from `@/components/ui/*`.

## Files

| File | Responsibility |
|------|----------------|
| `ErdGraphvizCanvas.tsx` | SVG output, toolbar wiring, domain merging. |

## A card's fills follow its contour

Graphviz draws a table card as an HTML-like label: the outline is a rounded rectangle
(`STYLE="ROUNDED"` on the `<TABLE>`), while the header band and the row tints are plain rectangles
painted inside it. Their square corners therefore stand outside the rounded corners of the card —
two tabs at the top, two more at the bottom whenever the last row is tinted.

The render effect closes that gap before the markup reaches the page: the string `gv.layout(...)`
returns goes through **`containNodeFills`** from **`@/lib/containNodeFills`**, which

- reads each node group's contour from the backdrop path the renderer emits — its bounds, and the
  corner radius from the path's first `M`;
- measures the **inset** the fills already keep from that contour (one unit today), which is also
  where a fill now stops, so the hairline between a fill and the stroke is exactly what it was;
- inserts one `<clipPath>` per card holding the contour shrunk by that inset as a rounded `<rect>`,
  and points every fill of the card at it.

The step is **markup-level and pure**, not a DOM pass: the check that guards it runs the very same
function in plain Node. It changes the drawing by insertion only — strip the clips and the markup is
byte-identical — and it is a no-op for a node that is not a card, which is why the lifecycle
automaton and the use-case diagram are untouched.

The geometry is derived, never assumed: a constant for the radius or the inset would be a defect the
day the renderer changes either. The check lives in
**`packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`** and runs in the repository's
closing check run; its printed `info` line says how many cards in the fixtures still show the defect
before the pass, which is a measurement, not an assertion.

## A dictionary's values, and a field that references one

A closed dictionary is an ordinary entity node whose payload carries two extra things: `entity_kind`
identifies the kind, and `values` is the list of declared codes, labels and descriptive properties in declaration order. The card
draws those values as rows under the fields, with no PK/FK marker and a green tint, so a reader sees
what the dictionary can hold without opening it. Each value's `properties` is an array of `{name, value}` text rows; these appear beneath the label, with HTML escaping applied to both names and values.

A field whose type is a dictionary carries `reference_qualname`. The card shows the dictionary's
short name after the type in teal, prefixed with an arrow: the field is not a string, it is a reference,
and the payload names the target.

## Render the server's group label once

The group response contains a complete `label`, for example
`pressing (by VinylRecordKindEnumEntity)`. `buildDotSource` escapes and displays that text;
it does not append a dictionary name. `dictionary_label` is absent from the current
`ErdGroup` type and response schema. It still exists in the underlying graph metadata,
which the server reads to produce the label. A stale extra field on an old payload must
not cause the name to be appended again.

The property list is a display representation: strings remain text and other JSON values
arrive as JSON text. Empty properties produce no extra lines. `check-erd-dictionary-values.ts`
checks escaping and actual SVG rendering; `check-erd-group-label.ts` checks that a complete
label remains unchanged, including with a stale dictionary_label beside it.

Nothing here knows a domain's vocabulary: every name comes from the payload, and a model that declares
no dictionary has an empty `values` array, and ordinary scalar fields have no `reference_qualname`.
