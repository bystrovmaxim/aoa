# Tasks: A table card's fills stop at its rounded outline

**Input**: Design documents from `specs/009-erd-card-contour/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: the specification asks for one automated check (FR-013) that fails before the change and
passes after it. That check *is* the test work of this feature; there is no test framework in the
client and none is added. Its assertion set is fixed in
[contracts/check-script.md](./contracts/check-script.md) — A-1 … A-13.

**Organization**: by user story. All three stories change the same two files, so the phases are
ordered rather than parallel across stories: US1 builds the pass and its call site, US2 hardens it
for every layout, every edge case and the large model, US3 proves the other two diagrams are
untouched.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1, US2, US3 — the user stories of [spec.md](./spec.md)
- Every task names the file it touches

**Paths**: the client lives at `packages/aoa-maxitor/client`; the closing run at `scripts/`.

---

## Phase 1: Setup (2 tasks)

**Purpose**: the baseline and the environment the check needs.

- [x] T001 Record the defect as it stands: render one fixture card through `@hpcc-js/wasm-graphviz` with a throwaway probe and keep the node group it prints beside the rounded contour path — written to `specs/009-erd-card-contour/evidence/before-card-node.txt`: contour `0 … 233.71 × −130.4 … 0`, radius `12`, inset `1`, and five fill corners standing `4.56` units outside the inset contour — the band's two upper corners and the last row's two lower ones (research R3, R6)
- [x] T002 Confirm the check's environment: `packages/aoa-maxitor/client/scripts/` created, and a `.ts` file there run by plain `node` (25.8.2) imports `src/lib/buildDotSource.ts` and prints a DOT source; the probe is deleted and only the directory stays (contract: check-script.md, invocation and A-13)

**Checkpoint**: the defect has a written baseline and the check can exist without a dependency.

---

## Phase 2: Foundational (3 tasks — blocks every story)

**Purpose**: the drawing model and the check's gate.

- [x] T003 [P] Create `packages/aoa-maxitor/client/src/lib/containNodeFills.ts` with the drawing model of [data-model.md](./data-model.md): the contour bounds, the radius from the path's first `M`, the inset from the fills, `inset radius = radius − inset` clamped at 0 (V-2), the qualification of a card (rounded backdrop plus at least one fill, V-5), and a pass that so far returns its input unchanged (R3, R4)
- [x] T004 [P] Create `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`: the environment guard A-13 (Node older than 22.6 exits `2` with one line), the six fixtures — band + PK + FK + body rows, band-only, narrow, inside a dashed cluster, a plain card, and a lifecycle-style node — rendered through the same WASM build the client loads, the printed diagnostic line, and assertion **A-1** (every fill trimmed by its card's clip and no fill leaving the card's bounds, contract: A-1)
- [x] T005 Run the check and confirm it exits `1` with A-1 naming the unclipped fills — the adversarial baseline FR-013 asks for, reached without any assertion that wants a defect to exist

**Checkpoint**: the model is derived from the drawing, and the gate fails on the code as it stands.

---

## Phase 3: User Story 1 — a card reads as one shape (Priority: P1) 🎯 MVP

**Goal**: the header band and the row tints are cut at the contour, so no fill stands outside the
card or runs under its stroke.

**Independent Test**: run the check — A-1 … A-4 and A-8 pass — and open the reproduction link to see
a card whose band follows its arcs.

- [x] T006 [US1] Emit the clip in `packages/aoa-maxitor/client/src/lib/containNodeFills.ts`: one `<clipPath id="erd-fill-clip-<node>">` per card holding the inset contour with `clipPathUnits="userSpaceOnUse"`, referenced by `clip-path="url(#…)"` from every fill; skip a card that already carries one (I-1 … I-4, V-3, V-4; R2)
- [x] T007 [US1] Call the pass at its only call site: in `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx`, the string `gv.layout(...)` returns goes through `containNodeFills` before it becomes the markup (R1)
- [x] T008 [US1] Extend `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts` with A-2 (every fill references its own card's clip), A-3 (the clip's bounds and radius are the contour's shrunk by the inset) and A-4 (a band-only card is clipped on all four corners) (contract: A-2 … A-4)
- [x] T009 [US1] Add A-8 to `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`: stripping the inserted clip elements and `clip-path` attributes restores the input byte for byte — the single assertion behind FR-002 … FR-005 and I-10
- [x] T010 [US1] Adversarial verification in `packages/aoa-maxitor/client/src/lib/containNodeFills.ts`: disable the pass so it returns its input, run `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts` and confirm A-1 … A-4 fail while A-8 stays green (nothing was inserted, so the drawing is trivially itself); restore the pass and confirm the whole check passes. The call site is not the lever here — the check calls the pass directly — so its presence is guarded by A-10 in T017

**Checkpoint**: US1 is done — the picture is right and a check keeps it right. This is the shippable increment.

---

## Phase 4: User Story 2 — the shape holds in every layout (Priority: P2)

**Goal**: the containment survives all five presets, every rebuild, the spec's edge-case cards and a
model of 120 tables.

**Independent Test**: the check renders the same fixture through all five presets, the narrow and
clustered cards, and a 120-card model; every assertion passes and the scale numbers are printed.

- [x] T011 [P] [US2] Add A-9 to `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`: applying the pass twice produces the same markup as applying it once (I-8, V-4)
- [x] T012 [US2] Add the five-preset fixture to `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts` — `gv-dot-lr`, `gv-dot-tb`, `gv-neato`, `gv-fdp`, `gv-circo` — asserting A-1 in each, so the containment is proven for every layout the viewer offers (FR-006, R5)
- [x] T013 [US2] Read the render effect in `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx`: `dot` is memoised over the merged payload and the layout, the render effect is keyed on `[dot, layout, bundleVersion, resetFitFlag]`, `setSvgMarkup` has exactly one call site (the pass), and the markup reaches the page through one `dangerouslySetInnerHTML` — so layout switches, domain filters, one-hop toggles and graph reloads all pass through it; no move was needed (FR-007, FR-011)
- [x] T014 [P] [US2] Add A-5 to `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`: a card narrower than twice the corner radius is processed, its inset radius clamps at 0, and no fill escapes the resulting shape (FR-009, V-2)
- [x] T015 [P] [US2] Add A-6 to `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`: a card inside a dashed specialization cluster is clipped, and the cluster's own frame is drawn as before (FR-008)
- [x] T016 [P] [US2] Add A-12 to `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`: a 120-card fixture renders and is processed in under 2000 ms, and both measured numbers are printed on the last line (FR-016, R6)

**Checkpoint**: US1 and US2 hold — the shape is right in every state the viewer can be in, on every
card the spec names, and at scale.

---

## Phase 5: User Story 3 — the other two diagrams are untouched (Priority: P3)

**Goal**: the lifecycle automaton and the use-case diagram draw exactly what they drew before, and
the change cannot spread to them unnoticed.

**Independent Test**: A-7, A-10 and A-11 pass, and the two pages are compared by hand before and
after.

- [x] T017 [US3] Add A-7, A-10 and A-11 to `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`: a lifecycle-style node comes back byte-identical (A-7), `containNodeFills` is imported by exactly one client source file (A-10), and neither production module imports a new package (A-11) (FR-010, FR-012, I-6)
- [x] T018 [US3] Draw the lifecycle automaton and the use-case diagram from the payload the check uses in `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`: both real builders are rendered through the graphviz the page loads, the pass is applied, and the bytes are compared — lifecycle 3791 B and use-case 2078 B come back byte-identical, asserted by A-7 on every run instead of by eye once (FR-010, SC-004). The glance at the two live pages stays in the pull request's evidence

**Checkpoint**: all three stories hold; the change is regression-bounded.

---

## Phase 6: Polish & the closing three steps

- [x] T019 Wire the check into `scripts/run_checks_with_log.sh`: one `run_and_log` step immediately after the client build, running `node scripts/check-erd-card-containment.ts` from `packages/aoa-maxitor/client` (R7, contract: wiring)
- [x] T020 Walk [quickstart.md](./quickstart.md) §1–§4: the check by command, the markup by eye through `--print-svg` (the mode had to be written — the contract promised it and the script did not have it), and the guard pages. §3, the reproduction link, needs a browser on a build that carries this change and stays with the pull request's evidence
- [x] T021 Measure the 120-card cost on the fixture of `packages/aoa-maxitor/client/scripts/check-erd-card-containment.ts`: seven runs, medians — drawing alone 17.4 ms, the pass 5.0 ms, so the drawing step is 1.29× its own time, inside the 1.5× bound (FR-016, SC-007). The in-page frame numbers need the built page in a browser and ride with the pull request's evidence, as agreed in the clarification session
- [x] T022 Run `bash scripts/run_checks_with_log.sh` and take it to zero — the only remarks left are the two the constitution accepts (the Vite chunk-size advisory and LangGraph's pending-deprecation warning) — **tail step 1 of 3**
- [x] T023 Write the documentation: `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/README.md` (what a card is, and that its fills follow its contour) and `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/README.md` (the pass, why it is markup-level, what it derives, the hairline the renderer's inset leaves, and the diagnostic line) — **tail step 2 of 3**
- [x] T024 Write the changelog as one article under `## [Unreleased]` in `packages/aoa-maxitor/CHANGELOG.md` — what the reader now sees, in plain words, with no per-file account — and its Russian draft in `packages/aoa-maxitor/CHANGELOG.ru_draft.md`, which is git-ignored and never committed — **tail step 3 of 3**

---

## Requirement coverage

Every requirement of [spec.md](./spec.md) has an owner. A requirement proven by an assertion names
it; a requirement proven by a person's eye names the task and the page.

| Requirement | Proven by | Tasks |
|---|---|---|
| FR-001 no fill outside the contour | A-1 | T004, T006, T008 |
| FR-002 the outline is unchanged | A-8 (byte identity) | T009 |
| FR-003 the fills keep their colour and row | A-8 | T009 |
| FR-004 the text is unaffected | A-8 | T009 |
| FR-005 edges, arrows, labels, canvas unaffected | A-8 | T009 |
| FR-006 all five presets | A-1 per preset | T012 |
| FR-007 every zoom and pan, after a rebuild | A-9, rebuild audit, the page | T011, T013, T020 |
| FR-008 a card inside a dashed container | A-6 | T015 |
| FR-009 a card narrower than twice the radius | A-5 | T014 |
| FR-010 the other two diagrams unchanged | A-7, A-10, the two pages | T017, T018 |
| FR-011 survives a re-render | A-9, rebuild audit | T011, T013 |
| FR-012 no new runtime dependency | A-11 | T017 |
| FR-013 an automatic check in the closing run | A-1 is the gate; the wiring | T004, T005, T019, T022 |
| FR-014 documentation and changelog ship | the two READMEs, the article | T023, T024 |
| FR-015 trimmed by the renderer's inset | A-1, A-3 | T006, T008 |
| FR-016 a large model stays usable | A-12, the recorded numbers | T016, T021 |
| SC-001 zero protruding corners in the default layout | the reproduction page | T020 |
| SC-002 zero in all five presets | A-1 per preset | T012 |
| SC-003 the gap to the stroke is unchanged | A-1, before-and-after measurement | T008, T020 |
| SC-004 the other two drawings are identical | A-7, the recorded comparison | T017, T018 |
| SC-005 the run carries the check and is green | the wiring, the closing run | T019, T022 |
| SC-006 the reader is told what a card is now | the READMEs and the article | T023, T024 |
| SC-007 120 tables and the 1.5× bound | the recorded numbers | T021 |

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: after Setup. T005 depends on T003 and T004.
- **US1 (Phase 3)**: after Foundational. T006 before T007; T008 and T009 after T006 and T007; T010 last.
- **US2 (Phase 4)**: after US1. T011, T014, T015 and T016 are independent of one another; T013 reads
  the call site T007 created.
- **US3 (Phase 5)**: after US1 (it asserts what the pass leaves alone); independent of US2.
- **Polish (Phase 6)**: T019 after T016 (the check must carry the scale assertion before the run
  carries the check); then the tail strictly in order — T022, T023, T024.

### Within the stories

- A-1 comes **before** any fix and is the gate that fails on today's code; every other assertion
  comes after the code it asserts.
- The call site (T007) comes before any assertion that needs the fixed markup.
- The wiring (T019) comes after the check is complete, and the closing run (T022) after the wiring.

### Parallel opportunities

- T003 and T004 — different files, no shared state.
- T011, T014, T015, T016 — four assertions appended to one check file: they are marked [P] for
  independence of content, but they collide in the same file — write them in any order, one at a
  time against the same tree, or fold them into one editing pass.
- T018 does not touch code and can run beside the check work.
- T023 and T024 are ordered by the constitution and are **not** parallel: documentation, then the
  changelog.

---

## Parallel Example: Phase 2

```bash
# Two different files, no dependency between them:
Task: "T003 — containNodeFills.ts: derive the contour, the radius and the inset"
Task: "T004 — check-erd-card-containment.ts: the fixtures, the environment guard and A-1"
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Setup (T001, T002) — baseline and environment.
2. Foundational (T003, T004, T005) — model derived, gate failing.
3. US1 (T006 … T010) — clip emitted, call site wired, containment and additivity asserted,
   adversarially verified.
4. **Stop and validate**: the check is green, and the reproduction link shows a card that reads as
   one shape. That alone is the issue fixed.

### Incremental delivery

- US1 → the picture is right, and nothing but the outlines moved (A-8).
- US2 → the picture stays right in every preset, every rebuild, the edge-case cards and on 120 tables.
- US3 → the other two diagrams are proven untouched, and the change cannot spread unnoticed.
- Polish → the check is part of the closing run, and the change has its three last steps.

### Where the work ends

The change is **prepared, not shipped**: nothing is committed, pushed or opened as a pull request.
Per constitution I that is a separate instruction from the maintainer, given in the conversation.

---

## Notes

- `[P]` marks different files, or work that does not collide.
- The check is the feature's test; its gate A-1 fails on today's markup, which is the demonstration
  the specification demands (FR-013), and A-8 proves the fix is additive.
- A constant `12` or `1` in `containNodeFills.ts` is a defect: the geometry is derived (V-1).
- Every fill and every card is accounted for in the check's printed counts, so a silent skip shows.
- The diagnostic line about the renderer is printed, never asserted: a future renderer that rounds
  its own cells should make the pass removable, not make the check red.
- The tail is three tasks, in this order and no other: T022 check run, T023 documentation, T024
  changelog (constitution VI).
