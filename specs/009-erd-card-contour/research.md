# Phase 0 — Research: a table card's fills stop at its rounded outline

**Feature**: `specs/009-erd-card-contour` | **Date**: 2026-10-18

Every unknown in the plan's Technical Context is resolved below. The measurements come from the
same renderer the client loads (`@hpcc-js/wasm-graphviz`, Graphviz 14.1.4) and from the production
builder `src/lib/buildDotSource.ts`, not from a mock.

## R1 — Where the trimming happens: a pure pass over the rendered markup, not a DOM pass

**Decision**: the trimming is a pure function over the SVG markup —
`containNodeFills(svg: string): string` in `packages/aoa-maxitor/client/src/lib/containNodeFills.ts` —
applied in `ErdGraphvizCanvas` to the string `gv.layout(...)` returns, before it is injected into the
page. The existing DOM post-pass (`postProcessGraphvizSvgDom`) is untouched and keeps running after
injection, as today.

**Rationale**

1. The check run has no browser and no DOM implementation. A string-level function is testable in
   plain Node, and the very same function the browser runs is the one the check exercises — not a
   parallel implementation.
2. Node 25.8.2 runs a `.ts` script that imports another `.ts` module directly (types are stripped,
   no bundler, no flags), verified by running the real `buildDotSource` from a throwaway script.
   So the check can use production code and needs no new dependency.
3. The ERD canvas is the only call site, so the lifecycle and use-case drawings cannot be affected
   (FR-010) by construction rather than by a heuristic.
4. FR-012 holds: no runtime dependency is added, and the drawing stays self-contained.

**Alternatives considered**

- *A DOM pass inside `postProcessGraphvizSvgDom`, with `jsdom` for the check.* Exercises the
  production path through a DOM too, but adds a dev dependency and a second dependency tree to
  `npm ci`, and tests jsdom's SVG behaviour rather than the drawing's geometry. Rejected.
- *Rewriting each fill polygon into a path with corner arcs.* More code, must be redone for every
  kind of row, and the same arithmetic appears once per fill. Rejected as more places to be wrong.
- *Squaring the card or shrinking the band so the rectangle stops looking wrong.* Refused by the
  specification: the outline is not the defect.

## R2 — Clip the fills to one contour per card, instead of re-shaping every fill

**Decision**: for each card, one `<clipPath id="erd-fill-clip-<node id>">` holding the inset contour
path, referenced by every filled shape of that group through `clip-path="url(#erd-fill-clip-<id>)"`.
The fills' own markup is not rewritten.

**Rationale**: one clip covers the header band, the primary-key tint, the foreign-key tint and the
body rows at once, and the straight edges are unchanged by construction — the fills already sit on
the inset contour (measured below), so only the corners are cut.

**Alternatives considered**: per-shape clipping (same result, more markup); re-shaping (R1);
`mask` (heavier and needs a paint server). Rejected.

## R3 — The geometry is derived from the drawing, never assumed

**Decision**: for each card the pass reads

- the **contour** from the backdrop path Graphviz emits first inside the node group
  (`<path fill="white" stroke="none" d="M12,0C12,0 …"/>`),
- the **bounds** from the coordinate extent of that path,
- the **corner radius** from the first `M` command's horizontal offset (`M12,0` → 12),
- the **inset** every fill keeps from the contour, from the smallest coordinate among the fill
  polygons,
- the **inset radius** as `radius − inset`.

Measured on a minimal card (one header plus one field row):

```text
rect        0 … 102.03  ×  −45.6 … 0
radius      12
inset       1
inset radius 11
fills       4
```

The numbers scale with the card, the radius and the inset do not: the five-field `ShowcaseEntity`
card of the issue measures `0 … 233.71 × −130.4 … 0` with the same radius `12` and the same inset
`1`, and sixteen fills. Both measurements are in
`evidence/before-card-node.txt`; deriving rather than hard-coding is what makes one pair of numbers
cover both.

**Rationale**: FR-015 and the assumption that the renderer may change its numbers; a constant that
matches Graphviz 14.1.4 is a defect waiting for the next Graphviz.

**Alternatives considered**: hard-coded 12 and 1. Refused by the spec.

## R4 — What counts as a card to clip

**Decision**: a node group is processed only when it has a backdrop path with an actual arc
(radius greater than 0) and at least one filled shape that is not that backdrop. A group carrying a
clip already is skipped, which makes the pass idempotent.

**Rationale**: a single-fill card (a card whose only row is the band) still needs all four corners
rounded, so "at least two fills" would be wrong; the FSM and use-case nodes carry their fill on the
node's own path with no backdrop polygon, so they never match. Everything else is returned
byte-identical.

## R5 — The pass runs on every render

**Decision**: the pass is applied where the markup is produced, so a layout switch, a domain filter
change, a one-hop toggle and a graph reload all go through it (FR-011). It is pure and idempotent:
the same input always yields the same output, and a second application changes nothing.

## R6 — Verification: a dependency-free check whose gate fails on today's code

**Decision**: `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`, run by plain
`node` (no framework, no new dependency). It imports `buildDotSource` and `containNodeFills` from
source, renders the fixture through the same WASM build the client loads, and asserts:

1. **A-1 — containment, and it is the gate.** Every fill of every card references its card's clip,
   and no fill's own rectangle leaves the card's bounds. Before the change no fill is clipped, so
   A-1 names the unclipped fills and the script exits `1`; after the change the same assertion
   passes on the same input.

   **Why not a point test** (found while building the check): a clip does not move the polygon's
   points, it decides what is painted. "Every fill point lies inside the inset contour" is
   therefore false even after the fix, and a check asserting it would be red forever. The two
   halves above are the properties that actually make an escape impossible; the corners that do
   stand outside are printed by the diagnostic instead.
2. **A-2, A-3 — the mechanism.** Every fill references its card's clip, and the clip's bounds and
   radius are the contour's shrunk by the inset.
3. **A-4 … A-6 — the shapes of the spec's edge cases.** A band-only card (four corners), a card
   narrower than twice the radius (inset radius clamps at 0), and a card inside a dashed
   specialization cluster (clipped, cluster frame unchanged).
4. **A-7 — the foreign node.** A lifecycle-style node — a single rounded path with a fill and no
   backdrop — comes back byte-identical (FR-010, by unit-level check and by A-10).
5. **A-8 — nothing else changed, proven rather than promised.** Remove the inserted `<clipPath>`
   elements and `clip-path` attributes from the processed markup and the result must equal the input
   byte for byte. This is the assertion for FR-002 … FR-005 and it replaces four separate ones: the
   contour, the colours, the text, the edges and the canvas are all covered by the same byte
   comparison.
6. **A-9 — idempotence**; **A-10 — the pass has exactly one call site** (a source scan);
   **A-11 — no new imports** (relative paths only) for FR-012.
7. **A-12 — scale.** A 120-card fixture renders and is processed in under 2000 ms, and the measured
   numbers are printed.

**Measured today** (fixture of 120 cards, 6 fields each): DOT build 1.1 ms, render 47.1 ms,
621 KB of markup. The 2000 ms budget is roughly a fortyfold headroom: it trips on a catastrophic
regression (an accidental quadratic walk, a backtracking expression over 600 KB of markup) and not
on a slow machine.

**One diagnostic, not asserted**: the script prints how many cards still show the defect in the
unprocessed markup. It is a measurement, not a gate — if a future renderer rounds its own cells, the
line reads zero and the pass becomes a candidate for removal instead of a check turning red for a
good upgrade.

**Rationale**: the clarification session chose an automatic check inside the check run, and chose
to record frame timing rather than assert it.

**Alternatives considered**: `vitest` + `jsdom` (a runner and a dependency for one geometry
assertion); Playwright (a browser download); asserting only on screenshots (refused by the
clarification session); asserting that the defect exists (passes on today's code, so it cannot be
the gate — the analysis pass caught exactly this).

## R7 — Where the check plugs into the closing run

**Decision**: one line in `scripts/run_checks_with_log.sh`, immediately after the client build step:

```bash
run_and_log "(cd packages/aoa-maxitor/client && node scripts/check-erd-card-containment.ts)" "Maxitor client: ERD card containment"
```

It runs after `npm ci`, so `node_modules` and the WASM package are present, and it adds no tool to
the run.

## R8 — Documentation and changelog homes

**Decision**

- `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/README.md` — what a card is and
  that its fills follow its contour.
- `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/README.md` —
  the pass, why it is a pure markup step, and what it derives.
- `packages/aoa-maxitor/CHANGELOG.md`, one article under `## [Unreleased]`, with its Russian draft in
  `packages/aoa-maxitor/CHANGELOG.ru_draft.md` (a `_draft` file, git-ignored, never committed).

**Rationale**: the component READMEs are the pages the closing run already requires beside every
`index.ts` under `components/`. For the changelog the evidence is the history: `docs/CHANGELOG.md`
has not been touched since 2026-10-08, and none of #199, #202, #213, #216, #220 or #221 appears in
it — every one of those changes is recorded in its package's changelog.

## R9 — Performance of the pass itself

**Decision**: one clip path and one attribute per card, a single linear walk over the markup, no
per-row work. Its cost is measured and printed by the check (R6.7) and by hand on the page for
SC-007; FR-016's 1.5× bound is verified by hand and recorded in the pull request, not asserted in
the run.

**Rationale**: the clarification session drew exactly this line — the scale fixture is asserted
against a generous wall-clock budget, the frame timing is recorded.

## R10 — The check must not break the run on an older Node

**Decision**: the script checks `process.versions.node` before anything else and exits `2` with one
explicit line when it is older than 22.6 — the first release that strips TypeScript types by itself
and therefore the first that can run a `.ts` check at all.

**Rationale**: the check runs inside the closing run, which developers and CI share. On a machine
with an older Node the plain failure would be a syntax error from a file the reader did not open,
and the run would look broken for a reason unrelated to the change. One line naming the requirement
turns that into an instruction.

**Alternatives considered**: rewriting the check in plain `.mjs` and importing only `.mjs` copies of
the logic (a duplicate of the module for the test, refused by R1); pinning the Node version for the
whole run (out of scope for this feature).

## Summary of decisions

| # | Question | Decision |
|---|----------|----------|
| R1 | Where the trimming happens | Pure markup pass, applied before injection; no new dependency |
| R2 | What is trimmed | One clip per card, referenced by every fill |
| R3 | Where the numbers come from | Derived from the drawn contour and the fills |
| R4 | Which groups qualify | Rounded backdrop plus at least one fill; already-clipped groups skipped |
| R5 | When it runs | On every render; pure and idempotent |
| R6 | How it is proven | A Node check that fails on today's markup and passes after |
| R7 | Where the check lives | One step in `scripts/run_checks_with_log.sh` |
| R8 | Where it is documented | Two component READMEs and the package changelog |
| R9 | What it costs | One clip and one attribute per card, measured and printed |
| R10 | What if Node is old | The check exits `2` with one explicit line before doing anything |
