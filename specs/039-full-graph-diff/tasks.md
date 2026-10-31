# Tasks: Maxitor Compares Two Versions on the Full Graph

**Input**: Design documents from `specs/039-full-graph-diff/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: included: the plan's checks and the house rule of adversarial verification (break the code the way the new test must catch, confirm that test fails and no other does, restore).

**Paths**: `F` = `packages/maxitor/front`, `FC` = `packages/maxitor/front/client`.

**Commits**: only on the maintainer's word (Principle I). Each phase below is one commit, except the closing one, which is three; tick the issue's box when a commit lands.

## Phase 1: The specification

- [ ] T001 Prepare commit 1 with `specs/039-full-graph-diff/` (`tasks.ru_draft.md` stays out): `docs(spec): specify comparing two versions on the full graph (#291)`.

---

## Phase 2: The union on the full graph (issue phase 1; US2)

**Goal**: A pair has one union, one layout on every engine, its own remembered arrangement.

**Independent Test**: The union's golden hash holds; the same layout in three engines; a second opening runs no layout.

- [ ] T002 Confirm the `edges` view's `payload` carries `field_name` and `from_state` in `F/src/maxitor/front/model/diagrams/resources/duckdb_graph_resource.py`; add them if not (research R1).
- [ ] T003 `F/src/maxitor/front/model/diagrams/actions/full_graph_action.py`: each edge's `id` is the protocol's, by `maxitor.graph_compare`'s rule; each node gains `data.type_slug` (contracts/maxitor-api.md). Update `FC/src/model/fullGraph.ts`.
- [ ] T004 Tests in `F/tests/test_full_graph_payload_shape.py`: every edge's id equals the graph document's on the demo graph, a `1.0` graph included; a `1.0` graph with an edge the rule refuses, and one with colliding ids, still answer. Confirm `FC/.../layoutDeterminism.test.ts`'s golden hash does not move; refresh `__fixtures__/full-graph-ref.json` only if its shape requires.
- [ ] T005 `FC/src/api/fullGraph.ts`: `fullGraph(read?)` reads a given version; export `domainMembers(payload)`, used by `buildDomainBubblePlugins`, and export the plugin builder for the union.
- [ ] T006 [P] [US2] `FC/src/lib/fullGraphDiff.ts`: `unionFullGraph(older, newer, compared)` per data-model.md: nodes sorted by `(lower(type_slug), lower(title), id)` and edges by `(source, target, type, relationship)` by code point, never `localeCompare`; `data.diff`; the `<id>#was` companion; maps merged, B winning.
- [ ] T007 [P] [US2] `FC/src/lib/fullGraphDiff.test.ts`: every status; a retargeted relation; a graph with itself gives the action's order, a non-ASCII label included; swapped arrival order gives the same union; every id once.
- [ ] T008 [US2] `FC/src/components/diagrams/FullGraphViewer/FullGraphViewer.tsx`: in Diff (`getActiveBase()`) `loadInterchange` reads B, A and `compareVersions()` and builds the union; the viewer's layout and arrangement effect runs on it unchanged; a pair changed while a layout runs is dropped (the existing `cancelled`). Live follows through the existing fresh-graph path.
- [ ] T009 [US2] `FC/.../FullGraphViewer/layoutDeterminism.test.ts`: a golden hash of a fixed union; a test that a union's fingerprint differs from each version's (`arrangementStore.test.ts`); a test that a remembered union runs no layout (`computeForceLayout` not called).
- [ ] T010 [US2] `FC/scripts/check-layout-determinism.ts`: its server answers a two-version history (the reference graph and a fixed edit), and the full graph in Diff joins the pages compared (research R9).
- [ ] T011 Adversarial: break the sort, the order of `#was`, and the id rule, one at a time; each named test fails alone; restore. Check run green; prepare commit 2: `feat(maxitor): the full graph lays out the union of two versions (#291)`; tick issue phase 1.

---

## Phase 3: Drawing the comparison (issue phase 2; US1, US3)

**Goal**: The marks, the counts and the card.

**Independent Test**: On the extended stand, every mark equals the comparison and the button equals the marks.

- [ ] T012 Extend `.demo-history/build_erd_full.py` (out of git) with the cases of the spec's "The acceptance stand"; rebuild; rewrite `.demo-history/erd-full.url`; confirm with `compare` that each case is there.
- [ ] T013 [P] [US1] `FC/src/lib/fullGraphDiff.ts`: `graphCounts(nodes, edges)` per data-model.md; `FC/src/lib/erdDiff.ts`: `DiagramCounts` gains `edgesMarked`; `nothingChanged` reads it; ERD passes `false`.
- [ ] T014 [US1] `FullGraphViewer.tsx` `buildGraph`: node style by `data.diff` (2.4 px ring in the ERD marks' green and amber; removed: white fill, dashed red stroke; unchanged opacity 0.28); edge style (status colour, removed dashed, unchanged 0.35; `was`: thin dashed); hover's states left as they are. Nothing marked: drawn as One (FR-013).
- [ ] T015 [US1] `FullGraphViewer.tsx`: hover label carries `+`, `−` or `~`; `setDiffCounts` on draw, `null` on unmount; `FC/src/components/history/VersionButton/VersionButton.tsx` reads `+0 −0 ~0` for edges only.
- [ ] T016 [US3] `FC/src/lib/erdDiffCard.ts`, `FullGraphViewer.tsx`: `node:click` on a marked node opens `DiffCard`; closing and following Live as in spec 038; an unchanged node as in One.
- [ ] T017 [P] [US1] Tests: `FC/src/lib/fullGraphDiff.test.ts` for counts; `FC/src/components/history/VersionButton/` for the edges-only reading.
- [ ] T018 [US1] Walk the marks, counts and card on the stand in the browser pane, B on Live with the live file changed; adversarial: invert a mark, count an edge, drop `edgesMarked`; restore. Check run green; prepare commit 3: `feat(maxitor): the full graph marks what changed between two versions (#291)`; tick issue phase 2.

---

## Phase 4: Filters (issue phase 3; US4)

**Goal**: Node types, domains and changes hide nodes, moving nothing.

**Independent Test**: Switching any filter moves 0 nodes; the counts equal the drawn marks.

- [ ] T019 [P] [US4] `FC/src/lib/fullGraphDiff.ts`: `visibleGraph(payload, off, membership)` by the data-model rule: "A node is shown when its type is on, its change is on, and it is in no domain or in at least one domain that is on. An edge is shown when both ends are." Tests beside it.
- [ ] T020 [US4] `FC/src/components/ui/ErdFilterPanel/ErdFilterPanel.tsx`: a `kindsTitle` prop; test and README.
- [ ] T021 [US4] `FullGraphViewer.tsx`: `usePageSetting` for `disabled_node_types`, `disabled_domains`, `disabled_changes`; the panel in place of `NodeTypeLegend`; hide and show without layout; hulls follow (research R6); counts and fading follow (R5). An open card whose node is hidden closes; a filter naming what the pair lacks has no effect.
- [ ] T022 [US4] `FC/src/lib/viewUrl.ts` and its test: the address carries the three settings. Remove `FC/src/components/ui/NodeTypeLegend/` if nothing imports it.
- [ ] T023 [US4] `FC/.../FullGraphViewer/README.md`: the new files and the panel. Walk the filters on the stand, a room of two tabs and phone width; adversarial: move a node on filter, hide an in-no-domain node, break the "all domains off" rule; restore. Check run green; prepare commit 4: `feat(maxitor): filters on the full graph (#291)`; tick issue phase 3.

---

## Phase 5: Closing (issue phase 4)

- [ ] T024 The closing check run: `bash scripts/run_checks_with_log.sh`, every remark fixed but the two accepted; walk `quickstart.md` by hand on the stand. Prepare a commit only if it edited anything.
- [ ] T025 The documentation: a page in `docs/` on comparing on the full graph, every case as a script and a notebook under `examples/step_26_maxitor/`, executed; the page's `.ru_draft.md` beside it. Commit: `docs(maxitor): compare two versions on the full graph (#291)`.
- [ ] T026 The changelog: one article in `docs/CHANGELOG.md`. Commit: `docs: changelog — comparing two versions on the full graph (#291)`; tick issue phase 4.

---

## Dependencies

- Phase 2 needs nothing but the spec. Phase 3 needs Phase 2. Phase 4 needs Phase 3's marks and counts. Phase 5 is last.
- [P] tasks touch different files: T006 with T007 in pairs of code and test; T013 with T017; T019 with T020.

## Implementation Strategy

Phases run in order, each ending in a walk and a check run. The first thing visible is Phase 3 on the stand; no phase is shown as a partial result.
