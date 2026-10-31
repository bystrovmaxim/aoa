# Tasks: Maxitor's Full Graph as a Map

**Input**: Design documents from `specs/040-full-graph-map/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: included: the plan's checks and the house rule of adversarial verification (break the code the way the new test must catch, confirm that test fails and no other does, restore).

**Paths**: `F` = `packages/maxitor/front`, `FC` = `packages/maxitor/front/client`, `GM` = `packages/maxitor/core/graph_map`.

**Commits**: only on the maintainer's word (Principle I). Each phase below is one commit, except the closing one, which is three; tick the issue's box when a commit lands.

**The mockup** in `.demo-history/map-demo` (out of git) is the reference for the look, and its outline and stepping code are the starting point of T029, T035 and T043.

## Phase 1: The specification

- [X] T001 Prepare commit 1 with `specs/040-full-graph-map/` (`tasks.ru_draft.md` stays out): `docs(spec): specify the full graph as a map (#319)`.

---

## Phase 2: The gear shift opens its section (US6)

**Goal**: On every diagram with the filter panel, moving the gear shift opens that section and folds the others.

**Independent Test**: On the ERD, in One and in Diff, move the gear shift and read which section is open.

- [X] T002 [US6] `FC/src/components/ui/ErdFilterPanel/ErdFilterPanel.tsx`: moving the gear shift opens that section and folds the others (FR-031); the section open at mount is the one that paints (FR-032); opening or folding by hand does not touch the paint; following a person keeps working (`useShownPanel`).
- [X] T003 [US6] Tests in `FC/src/components/ui/ErdFilterPanel/ErdFilterPanel.test.tsx`; the README says the rule.
- [X] T004 Adversarial: make the gear shift leave the section alone; make opening by hand change the paint; each named test fails alone; restore. Check run green; prepare commit 2: `feat(maxitor): the filter panel's paint switch opens its section (#319)`.

---

## Phase 3: The layout on the server (US5)

**Goal**: One version has one map, laid out once, and a domain that did not change keeps every position.

**Independent Test**: Lay out two versions differing in one domain; compare positions.

- [X] T005 `GM`: a new package like `packages/maxitor/core/graph_compare`: standard library only; `pyproject.toml`, workspace entry, `scripts/package_boundaries.toml`.
- [X] T006 [US5] `GM/.../areas.py`: from a graph document: drawn edges, membership by the client's rule, homes (first domain in order), `(outside)`, levels per data-model.md, content hash per area.
- [X] T007 [US5] `GM/.../bundles.py`: bundles between areas, with links by the types of their ends; counts by type.
- [X] T008 [US5] `GM/.../sketch.py`: the coarse grid per area, counts by type and status (research R6a).
- [X] T009 [US5] `GM/.../layout.py`: the DOT input of an area, stable by sorted ids, and reading `sfdp -Tjson0` with `overlap=scale`, the program passed in, so the package runs no process itself.
- [X] T010 [US5] `GM/.../places.py`: the registry of places (research R3): largest first, the nearest free spot beside what an area links to; a removed one keeps its place; one that outgrows its reserve moves alone.
- [X] T011 [P] [US5] Tests beside each module: homes for a node in several domains and in none; levels; bundle counts; the sketch's totals equal the counts; a place never overlaps; removing an element moves no other area.
- [X] T012 [US5] `F/src/maxitor/front/model/diagrams/resources/map_store.py`: a resource holding area layouts by content hash, places per history or source, and maps per version, on disk under the history cache; one layout at a time per version (FR-018); Live is laid out the same way, only its changed domains again (FR-019); it calls native `sfdp`, and refuses with a clear message when Graphviz is missing.
- [X] T013 `F/Dockerfile`: install Graphviz in the runtime image; `docs` of the local setup says `brew install graphviz`. Measure native `sfdp` on the generated graph and record it in research.md.
- [X] T014 Tests in `F/tests/test_map_store.py`: a second version lays out only the changed area; two readers share one layout; a restart reads what is stored; a failed area leaves the rest.
- [X] T015 Adversarial: drop the sort in the DOT; recompute all places per version; store by version, not by content; restore. Check run green; prepare commit 3: `feat(maxitor): lay the map out on the server, domain by domain (#319)`.

---

## Phase 4: Reading in parts (US1)

**Goal**: The browser reads an overview and one area at a time.

**Independent Test**: The contract's answers on the demo graph; sizes on the generated graph.

- [X] T016 [US1] `F/.../actions/map_overview_action.py`, `map_area_action.py` per contracts/maxitor-api.md: `laying-out` until ready; spec 037's rules for keys and logs. **A version with a stored map must not build its DuckDB first**: 23.6 s at this size; the middleware lets map reads through with the source named, and the store finds the map by the version's sha.
- [X] T017 [US1] `F/tests/test_map_actions.py`: shapes; a refused version; a wrong key reads "not found"; level 2 holds no level 3 node; `across` lists links to other areas.
- [X] T018 [US1] `FC/scripts/generate-large-graph.ts`: 30 copies of the stand's graph, linked across copies, with a version changing one domain (spec, "The acceptance stand").
- [X] T019 Check run green; prepare commit 4: `feat(maxitor): read the map in parts (#319)`.

---

## Phase 5: The map (US1, US2, US4)

**Goal**: The new viewer with levels, and the look approved.

**Independent Test**: The measured session; the walk on the stand; **the maintainer's approval**.

- [X] T020 `FC/package.json`: `sigma` 4, `graphology`, `@sigma/node-border`, `@sigma/node-image`.
- [X] T021 [US1] `FC/src/api/map.ts`: the reads; one opening reads each thing once (FR-013).
- [X] T022 [US2] `FC/src/lib/mapLevels.ts` and test: the level from the visible width, the reveal between thresholds, pure.
- [X] T023 [US2] `FC/src/components/diagrams/MapViewer/MapViewer.tsx`: Sigma set up per the mockup (`settings`, `primitives`, reducers): nodes with their icons rasterized once per type, links with arrows, camera, zoom and pan.
- [X] T024 [US1] `FC/.../MapViewer/areasLayer.ts`: areas on a canvas below the nodes: outlines as paths in graph space, tags that stay on screen and do not collide, what an area holds.
- [X] T025 [US1] `FC/.../MapViewer/bundles`: bundles between folded areas, fading out as detail comes.
- [X] T026 [US2] `FC/.../MapViewer/useAreaDetail.ts`: read what comes into view, keep about 3 000 nodes, let go the rest (FR-010 – FR-012); a folded area stays until its detail arrives.
- [X] T027 [US2] `MapViewer.tsx`: hover as today, with the HTML label; names by level; a click on a folded domain flies to it (FR-007 – FR-009).
- [X] T028 [US1] First paint: areas painted at once, Sigma taking over (research R7).
- [X] T029 [US4] Keep the overview's domain hull look: the outline from the sketch, with the mockup's field and contour, in `FC/src/lib/mapOutline.ts` and test.
- [X] T030 Replace `FullGraphViewer` with `MapViewer` where the diagram is chosen; remove `FullGraphViewer`, G6 and `@antv/layout` if nothing else imports them.
- [X] T031 [US4] `FC/scripts/measure-map.ts`: the scripted session on the generated graph, printing each SC-001 – SC-006 beside its threshold. Re-measure filters with `visibility`, as research.md asks.
- [ ] T032 Run the walk in **real Safari** with the existing `safariTab`; record it. **Moved to T047**, with the phone: it needs the maintainer at the machine.
- [X] T033 **The look gate.** Show the map beside today's graph on the stand. Stop here until the maintainer approves (FR-009a, SC-015).
- [X] T034 Adversarial: move a node between levels; drop the cap on loaded detail; restore. Check run green; prepare commit 5: `feat(maxitor): the full graph is a map (#319)`.

---

## Phase 6: The comparison on the map (US3, US7)

**Goal**: Everything #291 promised, from the server.

**Independent Test**: Every pair on the stand: marks and counts equal the comparison at every level.

- [X] T035 [US3] `GM/.../union.py`: the union of two maps: B's positions, an element only in A beside its neighbours, `was` on a retargeted relation, rules from spec 039; tests.
- [X] T036 [US3] The actions answer a pair with `a`; `F/.../actions/map_changes_action.py` lists the changes in the stepping order (FR-025b); tests.
- [X] T037 [US3] `FC/.../MapViewer`: rings, dashed removed nodes and links, fading, counts on folded domains, marked bundles; a domain where nothing changed is grey and dim at every level (FR-023).
- [X] T038 [US3] `FC/src/lib/diffCounts.ts`, `FC/src/lib/erdDiff.ts`, the version button: counts from the list of changes, nodes and links, whatever the zoom, so that they add up to the stepper's total; `App.tsx` passes counts on every diagram.
- [X] T039 [US7] The card on a marked node; on a touch screen too; `MARK_LOOK` moves to `erdDiffCard.ts`.
- [X] T040 [US3] Stepping: a click on a domain's count, and `FC/.../MapViewer/ChangeStepper.tsx` beside the version button, with the halo, per the mockup.
- [X] T040a [US3] FR-025d: `ChangeStepper.tsx` shares the version button's pill, arrows and chevron, and opens the list of changes, windowed, grouped by domain or table.
- [X] T040b [US3] FR-025e: the ERD steps too: `erdChanges` in `FC/src/lib/erdDiffCard.ts`, the drawn tables, rows and lines in order, each with its cell; `ErdGraphvizCanvas` goes to one and marks it.
- [X] T040c [US8] FR-025f: `Panels.changes` in `FC/src/rooms/focusStore.ts` and in the room's contract (`room_registry.py`): open, where the person stands, whether the card is open, the scroll; frames `change-steps` and `changes` for the pointer.
- [X] T041 Walk every pair of the stand, B on Live with the live file changed. Adversarial: count an edge; propagate a mark to a neighbour; step past the last; restore. Check run green; prepare commit 6: `feat(maxitor): compare two versions on the map (#319)`.

---

## Phase 7: Filters, paint and rooms (US6, US8)

**Goal**: The panel on the map, and everything that follows it.

**Independent Test**: Switch every filter at every level; a room of two browsers; a phone.

- [X] T042 [US6] `ErdFilterPanel`: `kindsTitle`; the full graph's panel with Domains, Node types and, in Diff, Changes; paint per FR-030, starting from Domains in One and Changes in Diff.
- [X] T043 [US6] `FC/src/lib/mapVisibility.ts` and test: what a filter set leaves, by the rule of data-model.md, **a hidden node taking what it contains with it (FR-028a)**; rows dim on their own axis and say what hides them (FR-028b, FR-028c), with `GM/.../assemble.py` counting nodes by type and the types above them; counts and bundles from the overview; **outlines, names and `45 of 394 left` follow at every level (FR-029a)**. Switching off Unchanged in Changes takes the grey domains off the map with their tags and bundles.
- [X] T044 [US6] `MapViewer`: hide without layout; filters under 50 ms, trying Sigma's data textures before a full refresh; re-measure.
- [X] T045 [US6] `FC/src/lib/viewUrl.ts` and test: `disabled_node_types`, `disabled_domains`.
- [X] T046 [US8] `FC/.../MapViewer/mapSurface.ts`: the room's surface in map coordinates: pointers, following, hover; the cross-engine check covers the map (research R10).
- [ ] T047 [US8] Phones: pinch, tap, the Filter pill, about 1 500 nodes kept; real Safari again; SC-018 measured on a real phone, with the maintainer. Done in emulation; the real phone and real Safari, with T032, need the maintainer at the device.
- [X] T048 No WebGL: the page says so and offers the ERD (FR-036). README of `MapViewer`.
- [X] T049 Walk the filters on the stand at every level, a room of two browsers, a phone. Adversarial: move a node on a filter; hide a node in no domain; leave an outline unchanged; restore. Check run green; prepare commit 7: `feat(maxitor): filters and paint on the map (#319)`.

---

## Phase 8: Closing

- [X] T050 The closing check run: `bash scripts/run_checks_with_log.sh`, every remark fixed but the two accepted; walk `quickstart.md`. Prepare a commit only if it edited anything.
- [X] T051 The documentation: a how-to page on reading the map, every case as a script and a notebook under `examples/step_26_maxitor/`, executed; the page's `.ru_draft.md` beside it. Commit: `docs(maxitor): read the full graph as a map (#319)`.
- [ ] T052 The changelog: one article in `docs/CHANGELOG.md`. Commit: `docs: changelog — the full graph as a map (#319)`; close #291 with a note, tick the issue. The article is committed; closing #291 waits for the maintainer's word, after the real phone and real Safari.

---

## Dependencies

Phase 2 stands alone. Phases 3 to 7 run in order. T033 stops the work until the maintainer approves the look. Phase 8 is last.

## Implementation Strategy

Phases run in order, each ending in a walk and a check run. No partial result is presented as finished; the thresholds are measured on the generated graph in T031 and T044, and if one cannot be reached the steps down are #319's, §5.
