# Implementation Plan: A table card's fills stop at its rounded outline

**Branch**: `feature/issue-226-erd-rounded-band` | **Date**: 2026-10-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/009-erd-card-contour/spec.md`

## Summary

Every card in the domain ERD is a Graphviz **HTML-like label**: the outline is rounded
(`STYLE="ROUNDED"` on the table), while the header band and the row tints are painted as plain
rectangles. The rectangles run through the rounded contour, so each card wears two orange tabs at the
top and — whenever the last row is tinted — two at the bottom.

The fix trims the fills instead of the shape. The markup the renderer returns is passed through one
new pure function, `containNodeFills(svg: string): string`, which derives the card's contour from the
drawn backdrop path, measures the inset every fill keeps from it, and gives the card a single
`<clipPath>` holding the contour shrunk by that inset. Every fill of the card references it, so the
band and the rows are cut at the inner edge of the stroke and nothing is painted outside or under it.

The function is pure markup work with no DOM, which is what makes the second half of the plan
possible: a check in plain `node` renders a fixture through the *same* WASM build the client loads
and runs the *same* function. Its gate is the containment assertion — every fill trimmed by its card's clip,
no fill leaving the card's bounds — and on the code as it stands no fill is clipped at all, so the
check exits `1`; after the change the same assertion passes. A second assertion strips the
inserted clips from the output and requires the input byte for byte, which is how the fix is
proven additive. No new dependency, runtime or dev.

## Technical Context

**Language/Version**: TypeScript 5.7 in the client (`packages/aoa-maxitor/client`), React 19, Vite 6;
the check is TypeScript executed by Node 25.8.2 directly (types stripped, no bundler, no flags).

**Primary Dependencies**: `@hpcc-js/wasm-graphviz` 1.21 (Graphviz 14.1.4, WASM) for layout; nothing
new is added — not at runtime, not in dev.

**Storage**: N/A — the client draws a payload the service already produces.

**Testing**: a standalone check script run by the repository's closing run
(`scripts/run_checks_with_log.sh`). There is no JS test framework in this repository and this plan
does not add one; the repository's Python suites are untouched.

**Target Platform**: browsers — the SVG is drawn by Chromium, WebKit and Firefox; `clipPath` with
`clipPathUnits="userSpaceOnUse"` is supported by all three.

**Project Type**: web client of a service; only the client changes.

**Performance Goals**: a diagram of 120 tables opens, pans and zooms without noticeable stutter and
is no more than 1.5× slower than today on the same machine (FR-016, SC-007). Measured today: 120
cards → 1.1 ms to build the DOT, 47.1 ms to render, 621 KB of markup.

**Constraints**: the ERD canvas is the only call site, so the lifecycle and use-case drawings cannot
change; the contour, its stroke, the colours, the text, the edges and the canvas stay byte-identical;
the pass is pure and idempotent; it never throws on markup it does not recognise.

**Scale/Scope**: one new module, one call site (one line), one check script with thirteen assertions,
one line in the closing run, two component READMEs and one changelog article. No service change, no
payload change, no new dependency.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Verdict |
|---|---|---|
| **I. The maintainer decides** | The plan must not commit, push, open a pull request or merge | **Pass** — nothing in this plan ships anything; the branch is prepared and shown. A commit is a separate instruction. |
| **II. English in commits, git and code** | Every artifact of the change is English | **Pass** — spec, plan, research, contracts, code comments, READMEs and the commit message are English. The Russian changelog draft is a `_draft` file, git-ignored, and never enters history. |
| **III. Module headers** | Python modules under `packages/*/src` open with their path, a title and the U+2550 rule | **Pass (not triggered)** — no Python module is added or touched. The new TypeScript module follows the client's own existing header convention, as `src/lib/buildDotSource.ts` does. |
| **IV. AI-CORE blocks** | Public classes and module-level functions carry the block | **Pass (not triggered)** — Python-only convention; the change adds no Python. |
| **V. Short docstrings** | Every class, function and method carries a one-line docstring | **Pass (not triggered for Python)** — the client is TypeScript; the new exported function carries the one-line JSDoc the client's modules already use. |
| **VI. The last three steps** | Check run → documentation → changelog, in that order, with three reserved tasks | **Pass** — the tail is planned as three separate tasks below and the check is the one this plan adds to the run. |

No principle is violated and no complexity is added, so the Complexity Tracking table stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/009-erd-card-contour/
├── plan.md                              # this file
├── spec.md                              # the specification
├── research.md                          # Phase 0 — nine decisions, measured
├── data-model.md                        # Phase 1 — the drawing model and its invariants
├── contracts/
│   ├── containment-pass.md              # the pass's promises
│   └── check-script.md                  # the check's invocation, exit codes and assertions
├── quickstart.md                        # Phase 1 — four ways to see it work
├── checklists/requirements.md           # spec quality checklist
└── tasks.md                             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
packages/aoa-maxitor/
├── client/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── containNodeFills.ts                      # NEW — the pure pass
│   │   │   ├── buildDotSource.ts                        # unchanged; the check imports it
│   │   │   └── sanitizeGraphvizSvgOverlays.ts           # unchanged; the DOM post-pass stays
│   │   └── components/diagrams/ErdViewer/
│   │       ├── README.md                                # UPDATED — what a card is now
│   │       └── parts/ErdGraphvizCanvas/
│   │           ├── ErdGraphvizCanvas.tsx                # UPDATED — one line, the call
│   │           └── README.md                            # UPDATED — the pass, and why markup-level
│   └── scripts/
│       └── check-erd-card-containment.ts                # NEW — the check
├── CHANGELOG.md                                         # UPDATED — one article under [Unreleased]
└── CHANGELOG.ru_draft.md                                # UPDATED — the Russian draft (git-ignored)

scripts/run_checks_with_log.sh                           # UPDATED — one step after the client build
```

**Structure decision**: the pass goes in `src/lib/` beside `buildDotSource.ts` because that is where
the client keeps markup-level, DOM-free helpers, and because the check must import it in plain Node —
a module under `components/` would drag JSX and the `@/` alias into that import path. The check lives
in `client/scripts/` because it is a repository tool, not client runtime: `tsconfig.json` includes
only `src`, so the script is deliberately outside the build.

## Phase 0 — Outline & Research

Resolved in [research.md](./research.md); the decisions that shaped the design:

| # | Unknown | Resolution |
|---|---|---|
| R1 | Where can the trimming live so the check can reach it? | A pure markup pass applied before injection — proven reachable: Node runs a `.ts` script that imports the production `.ts` directly |
| R2 | Clip the fills, or re-shape each one? | One clip per card referenced by every fill; straight edges are unchanged because the fills already sit on the inset contour |
| R3 | Where do the numbers come from? | Derived from the drawing: contour bounds, radius from the first `M`, inset from the fills. Measured: radius 12, inset 1, inset radius 11 |
| R4 | Which groups qualify? | A rounded backdrop plus at least one fill; a card with a single fill is included, a lifecycle-style node is not |
| R5 | When does it run? | On every render; pure and idempotent |
| R6 | How is it proven? | A dependency-free Node check whose gate (every fill trimmed by its card's clip, no fill leaving the card's bounds) fails on today's code, plus a byte-identity assertion that proves the fix additive |
| R7 | Where does the check plug in? | One step after the client build in `scripts/run_checks_with_log.sh` |
| R8 | Where do docs and the changelog go? | Two component READMEs plus the package changelog — evidenced by where #199, #202, #213, #216, #220 and #221 were recorded |
| R9 | What does it cost? | One clip and one attribute per card, one linear walk |
| R10 | What if the machine's Node is old | The check exits `2` with one explicit line naming Node 22.6 before doing any work |

**Output**: `research.md`, every NEEDS CLARIFICATION resolved — there are none left.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — the drawing model: Contour, Fill, Inset, Card, Clip; nine
  invariants (I-1 … I-9) and five validation rules (V-1 … V-5).
- **[contracts/containment-pass.md](./contracts/containment-pass.md)** — the pass's signature and its
  nine promises: total, pure, idempotent, selective, contained, conservative, deterministic,
  additive and linear.
- **[contracts/check-script.md](./contracts/check-script.md)** — invocation, exit codes, the
  thirteen assertions A-1 … A-13, the printed diagnostic, and the one line that wires it into the
  closing run.
- **[quickstart.md](./quickstart.md)** — the check, the markup by eye, the page, the regression
  guards, the 120-card numbers.

**Post-design constitution re-check**: unchanged from the table above — the design adds one
TypeScript module, one script and documentation, touches no Python, ships nothing, and keeps the tail
in three steps.

## Phase 2 — Implementation outline (for `/speckit-tasks`)

1. **The pass** — `containNodeFills.ts`: find node groups, qualify them (R4), derive the contour and
   the inset (R3), emit one clip per card and reference it from every fill (R2), skip what it does
   not recognise (V-5), and stay idempotent (V-4).
2. **The call site** — one line in `ErdGraphvizCanvas.tsx`, where the layout result becomes the
   markup.
3. **The check** — `scripts/check-erd-card-containment.ts` with A-1 … A-13, built in four
   increments by story: the gate and the environment guard first, then the mechanism and
   additivity, then the layouts, the edge-case cards and the scale fixture, then the foreign-node
   and import guards. A-1 is the gate and it fails on today's code by construction, because the
   pass returns its input unchanged.
4. **The wiring** — one step in `scripts/run_checks_with_log.sh`, after the client build.
5. **The closing check run** — `bash scripts/run_checks_with_log.sh` to zero, with only the two
   accepted tool remarks in the log.
6. **The documentation** — the two component READMEs.
7. **The changelog** — one article under `## [Unreleased]` in `packages/aoa-maxitor/CHANGELOG.md` and
   its `CHANGELOG.ru_draft.md` counterpart.

Steps 5, 6 and 7 are the constitution's tail and stay three separate tasks, in that order; step 6
takes no numbering from step 5 and step 7 is written last.

## Dependencies

- **None external.** The check imports `@hpcc-js/wasm-graphviz`, already a client dependency and
  already installed by the `npm ci` the closing run performs before the check's step.
- The check must run **after** `npm ci` and **before** the Python steps of the run, so that a broken
  drawing fails fast.
- The work depends on issue [#226](https://github.com/bystrovmaxim/aoa/issues/226) only.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| The pass mangles markup it does not understand | V-5: unrecognised groups are returned unchanged; A-7 asserts a lifecycle node is byte-identical, and A-8 catches anything else that moved |
| The geometry drifts when the renderer is upgraded | R3: everything is derived; a constant is a defect (V-1) |
| A browser renders the clip differently from the reference | The clip is a plain `clipPath` with `clipPathUnits="userSpaceOnUse"`; quickstart §3 checks all five presets in the page |
| The check becomes flaky on a slow machine | Only a wall-clock budget of 2000 ms against a measured 47 ms; frame timing is recorded, not asserted (FR-016) |
| The 120-card case slows the page | One clip and one attribute per card, one linear walk (R9); the page's numbers are recorded in the pull request |
| The change reaches the other two diagrams | The ERD canvas is the only call site, and the pass itself skips non-cards (FR-010); A-7, A-10 and A-11 assert it |
| The machine running the checks has an older Node | A-13: the check exits `2` with one explicit line naming Node 22.6 instead of failing on a syntax error (R10) |
| The pass quietly changes something besides the fills | A-8: stripping the inserted clips must restore the input byte for byte (I-10) |

## Out of scope

The card's radius, stroke and colours; the dashed cluster frame, the legend, the toolbar and the
empty state; edge routing, edge labels and arrowheads; the payload and the endpoints; the legacy
server-side HTML visualizer, which no longer exists in this package. The lifecycle and use-case
diagrams are a regression boundary, not a second scope.

## Completion criteria

- `node packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts` fails on the code before
  the change and passes after it, and its scale line prints both numbers.
- `bash scripts/run_checks_with_log.sh` is green, with only the two accepted tool remarks.
- The reproduction link shows no card whose fill leaves its contour, in all five presets.
- The two component READMEs describe what a card is and why the pass is markup-level; the changelog
  article and its Russian draft exist.
