# Contract — the card containment check

**Script**: `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts` (new)
**Runner**: the repository's closing check run, through `scripts/run_checks_with_log.sh`
**Date**: 2026-10-18 (revised after the analysis pass)

## Invocation

```bash
cd packages/aoa-maxitor/client
node scripts/check-erd-card-containment.ts
```

Plain `node` — no framework, no bundler, no new dependency. It must run after `npm ci`, because it
imports the client's installed packages (`@hpcc-js/wasm-graphviz`) and the production sources
(`src/lib/buildDotSource.ts`, `src/lib/containNodeFills.ts`). Node 25.8.2 was verified to execute
such a script and its `.ts` imports directly (R1, R6).

**Environment guard (A-13)**: types are stripped by Node itself, which needs Node 22.6 or newer.
The script therefore reads `process.versions.node` first and, on anything older, prints one explicit
line naming the requirement and exits `2` — it does not fail with a syntax error a reader would have
to decode.

**Optional mode**: `--print-svg` writes the fixture card's unprocessed and processed markup to stdout
instead of asserting, separated by a marker line, so the difference can be read as text
(quickstart §2). It exits `0` when both halves were produced and changes no assertion.

## Exit codes

- `0` — every assertion passed.
- `1` — at least one assertion failed; the failing assertion names the card, the shape and what was
  expected.
- `2` — the environment is not fit to run the check (Node older than 22.6, or the WASM package is
  not installed).

## The one diagnostic line

The script prints, without asserting on it:

```text
info  the renderer still emits rectangles: 4 of 6 cards have a fill corner outside the contour before the pass
```

This is the measurement that the pass is still needed. It is **not** an assertion: on the day the
renderer rounds its cells itself, this line reports zero and the work becomes a candidate for
removal, rather than a check turning red for a good upgrade.

## Output

What the check prints on the code as it stands.

```text
ok    A-13 environment  Node 25.8.2 runs this script directly
info  the renderer still emits rectangles: 13 of 14 cards have a fill corner outside the contour before the pass
ok    A-1 showcase  1 card(s), 16 fills trimmed to the inset contour
ok    A-1 band-only  1 card(s), 1 fills trimmed to the inset contour
ok    A-1 plain  1 card(s), 7 fills trimmed to the inset contour
ok    A-1 cluster  3 card(s), 12 fills trimmed to the inset contour
ok    A-1 narrow  1 card(s), 1 fills trimmed to the inset contour
ok    A-1 degenerate  1 card(s), 1 fills trimmed to the inset contour
ok    A-1 lifecycle  no card here — the node is left alone, and A-7 will assert it byte-identical
ok    A-1 use-case  no card here — the node is left alone, and A-7 will assert it byte-identical
ok    A-1 preset gv-dot-lr  1 card(s), 16 fills trimmed to the inset contour
ok    A-1 preset gv-dot-tb  1 card(s), 16 fills trimmed to the inset contour
ok    A-1 preset gv-neato  1 card(s), 16 fills trimmed to the inset contour
ok    A-1 preset gv-fdp  1 card(s), 16 fills trimmed to the inset contour
ok    A-1 preset gv-circo  1 card(s), 16 fills trimmed to the inset contour
ok    A-2 clip wiring  118 fills reference their own card's clip, each clip once per drawing
ok    A-3 geometry  13 clips are the card's contour shrunk by the inset, radius minus inset
ok    A-4 band-only card  the band spans the clip and all four corners are cut (radius 7.13)
ok    A-5 degenerate cards  the narrow card keeps a positive clip, and the inset that consumes the radius yields radius 0
ok    A-6 grouped card  3 cards clipped inside the dashed cluster, its frame byte-identical
ok    A-8 additive  13 drawings are byte-identical to their input once the clips are stripped
ok    A-9 idempotence  13 drawings are unchanged by a second pass
ok    A-12 scale  120 cards rendered and processed in 28 ms (budget 2000 ms, 607 KB)
ok    A-7 foreign nodes  byte-identical: lifecycle 3791 B, use-case 2078 B
ok    A-10 import guard  the pass is imported by components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx and by nothing else
ok    A-11 no new imports  neither drawing module imports anything at all, let alone a package
```

## Assertions

| # | Assertion | What it protects |
|---|---|---|
| A-1 | Containment, in the two halves that make paint outside the contour impossible: every fill of every card references its card's clip, and no fill's own rectangle leaves the card's bounds. It **fails on the code as it stands today**, because no fill carries a clip | FR-001, FR-015 |
| A-2 | Every fill carries `clip-path="url(#erd-fill-clip-<node>)"` and that clip is the card's own | R2 |
| A-3 | The clip's bounds equal the contour's bounds shrunk by the inset, and its radius equals `radius − inset` — read from the `<rect>`'s own `x`, `y`, `width`, `height` and `rx` | R3, FR-015 |
| A-4 | A card with only a band is clipped on all four corners | US1-4, FR-001 |
| A-5 | The degenerate cards are processed without a failure: a card whose arcs meet keeps a positive clip with the radius the derivation gives it, and a card whose inset consumes the whole radius gets `rx="0"` with every fill inside the clip | FR-009, V-2 |
| A-6 | A card inside a dashed specialization cluster is clipped, and the cluster's own frame is drawn as before | FR-008 |
| A-7 | The other two drawings — the real lifecycle automaton and the real use-case slice, from their own builders — come back byte-identical, and no card is found in either | FR-010, I-6 |
| A-8 | Stripping the inserted `<clipPath>` elements and `clip-path` attributes from the processed markup yields the input byte for byte | FR-002, FR-003, FR-004, FR-005, I-10 |
| A-9 | Applying the pass twice equals applying it once | I-8 |
| A-10 | `containNodeFills` is imported by exactly one client source file, the ERD canvas | FR-010, R1 |
| A-11 | Neither production module imports a new package; their imports are relative paths only | FR-012 |
| A-12 | A 120-card fixture renders and is processed in under 2000 ms, and both numbers are printed | FR-016, R6 |
| A-13 | On Node older than 22.6 the script exits `2` with one explicit line | M4 — the check must not break the run for a reason a reader has to decode |

**Why the gate is structural rather than a point test** (found while building the check): a clip does
not move a polygon's points — it decides what is painted. So "every point of every fill lies inside
the inset contour" can never pass, not even after the fix, and asserting it would have produced a
check that fails forever. What does hold, and is what the specification needs, is that the paint
cannot land outside: the fill's rectangle stays within the card's bounds, and the clip trims it to
the inset contour. The measured corners live in the diagnostic line, where a reader sees them.

**How "fails before, passes after" is satisfied**: A-1 is the gate. Before the change no fill is
clipped, so A-1 names the unclipped fills and the script exits `1`; after the change the same
assertion passes on the same input. A-8 then proves the fix touched nothing but the fills' outlines.

## Wiring

One step in `scripts/run_checks_with_log.sh`, immediately after the client build:

```bash
run_and_log "(cd packages/aoa-maxitor/client && node scripts/check-erd-card-containment.ts)" "Maxitor client: ERD card containment"
```

The step follows `npm ci`, so the installed tree the check needs is already there, and the closing
run gains no tool (R7).
