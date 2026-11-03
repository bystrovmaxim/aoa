# Tasks: Events explorer

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/events-explorer.md](contracts/events-explorer.md), [research.md](research.md). Tests are required: every phase is verified adversarially — break the rule the new test must catch, see that test fail and no other test of the phase, restore. The demo `packages/maxitor/web/client/explore-demo.html` with `src/demo/eventsExplorer/` is the reference of behaviour and is not committed.

Paths below are relative to `packages/maxitor/web/` unless they start with `docs/`, `specs/` or `packages/`.

## Phase 1: The data (one commit)

- [x] T001 Add the test graph `tests/fixtures/explorer_graph.py` (`explorer_graph()`, protocol 1.3): domains with a vocabulary, with an empty vocabulary, emitting without one, and with no events; events of the three standings (in vocabulary and emitted, emitted with no vocabulary, in vocabulary and not emitted); one event held by two vocabularies; one event emitted by an action of another domain without a vocabulary; actions without events; methods of all five kinds emitting
- [x] T002 Add `explorer_graph_b()` beside it: the same graph with one event and one `@emits` edge added, for Diff
- [x] T003 [US1] Add `maxitor/web/model/diagrams/actions/events_explorer_action_schema.py`: `EventsExplorerJson` per data-model.md "Wire" — `domains[] {id, label, short_label, accent_color, vocabulary: bool}`, `actions[] {id, label, short_label, domain_id}`, `events[] {id, label, fields[] {name, type, description}}`, `holds[] {domain_id, event_id}`, `emits[] {action_id, method_id, method, kind, event_id}`, `additionalProperties: false`
- [x] T004 [US1] Add `maxitor/web/model/diagrams/actions/events_explorer_action.py`: `events_explorer(duck)` (AI-CORE block) reading every domain (`typed_events` → `vocabulary`), every action with its domain, `domain_event` pairs, the five kinds of method and their `@emits`, events with fields; all lists sorted by id; and `GetEventsExplorerAction` (`DiagramsDomain`, `GuestRole`, DuckDB connection; FR-025, FR-026: only the graph document, no language assumed), reusing the helpers of the events diagram module moved into this one
- [x] T005 [US1] Route `GET /api/v1/events-explorer` to `GetEventsExplorerAction` in `maxitor/web/api/app.py`; the old routes stay until phase 2 removes the old view with them, so no commit leaves the client calling a route that is gone
- [x] T006 [US1] Add `tests/test_events_explorer_action.py`: every coverage and standing of T001 in the answer, an empty vocabulary as `vocabulary: true`, the five kinds, sorted lists, a 1.2 document giving domains and actions with empty `events`, `holds`, `emits`; the route through the app
- [x] T007 Rebuild `graph.json` with `graph-builder` and run `graph-builder check`
- [x] T008 Break each rule adversarially against this phase's tests (kind dropped, empty vocabulary as false, unsorted list), restore; run only this phase's tests; commit

## Phase 2: The explorer with its ports and lines (one commit)

- [x] T009 [US1] Add `client/src/model/eventsExplorer.ts` (wire types) and `client/src/api/eventsExplorer.ts` (`fetchEventsExplorer(base?)` through `graphFetch("/api/v1/events-explorer")`)
- [x] T010 [US1] Add `client/src/lib/eventsExplorer.ts`, part one: the graph index (vocabulary, holders, emits by action and by event, all actions by domain), coverage, standing, the count of a domain (data-model.md "Derived"), the neighbours of each port, roots by mode (FR-003: domains with events first then the others, by name; every event; every action that emits)
- [x] T011 [US1] Add `client/src/components/diagrams/EventsExplorer/` — `EventsExplorer.tsx`, `ModePill.tsx`, `ExplorerNode.tsx`, `index.ts`, `README.md`: the light pill of three modes with counts (FR-002), nodes per FR-004–FR-006, cards per FR-007 through the common `ElementCard`, the two layouts and the toolbar per FR-019 with a close-every-port button and the hover-cards switch
- [x] T012 [US1] Lay the screen out with Graphviz `dot` read back as `json` (research.md "Layout"): one HTML table per node with a cell per port, `ranksep` 2.8 LR / `nodesep` 0.7 TB (FR-020), the first layer chained `rank=same` in order; draw nodes as HTML and lines as SVG at Graphviz's positions, in `client/src/lib/eventsExplorer.ts` (DOT and reading) and the viewer
- [x] T013 [US1] Add `placeAt(clientPoint, contentPoint)` to `client/src/components/diagrams/ErdViewer/hooks/useSvgPanZoom.ts` and use the hook in the viewer with `fitToViewBox` (FR-021); a mode, filter or layout change fits (FR-022); a first layer too tall starts at its top, readable
- [x] T014 [US1] Show the explorer for both `events` and `events_all` in `client/src/components/pages/DiagramWorkspacePage/DiagramWorkspacePage.tsx`, the domain row with `domain:<id>>events` open (FR-001); remove `client/src/components/diagrams/EventsDiagramViewer/`, `client/src/lib/eventsDiagram.ts` with its test, `client/src/api/domainEventsDiagram.ts`, `client/src/model/domainEventsDiagram.ts`, and on the server `/domain-events-diagram`, `/events-diagram`, `domain_events_diagram_action.py`, `domain_events_diagram_action_schema.py`, `tests/test_domain_events_diagram_action.py`, rebuilding `graph.json`
- [x] T015 [US1] Add tests in `client/src/lib/eventsExplorer.test.ts`: counts of each coverage, roots and their order per mode, the first screen of Domains mode holding domains only (SC-002), neighbours of each port, a 1.2 answer

- [x] T017 [US2] In `client/src/lib/eventsExplorer.ts`: `explore(roots, opened, filters)` breadth first giving each shown node its layer; ports by layer (FR-009) — layer 0 both, layer 1 the one toward the kind not yet on the path, layer ≥ 2 one joining port toward the first layer's kind counting the shown nodes it would join that no line joins yet; empty ports with 0 and inert (FR-010); `+`/`−` and hidden counts (FR-008)
- [x] T018 [US2] In the same file: links — holds, domain-emits, emits (with its methods and kinds), belongs — drawn only between neighbouring layers or when an open joining port asks (FR-012); each leaves by the port of its kind
- [x] T019 [US2] [US3] In `client/src/components/diagrams/EventsExplorer/`: `PortPill.tsx` (stub line, icon, number, sign; dashed outline when joining), clicking a node opens its main port or its first non-empty one (FR-011), lines by kind and stroke without arrows (FR-013), the method's name beside the line's start on hover of the line or an end (FR-014), lighting on hover (FR-015), the clicked node held still and its new nodes brought into view through `placeAt` (FR-022), new nodes fading in
- [x] T020 [US2] [US3] Add tests in `client/src/lib/eventsExplorer.test.ts`: layers, ports per layer in each mode, joining counts and lines, no line across non-neighbouring layers, an event held by two domains joined to both, a closed port hiding only what no other open port shows, a port of a node off the screen remembered, every port's number equal to its elements under the filters (SC-003), the actions emitting an event of a domain reached in two clicks (SC-001)
- [x] T016 Break adversarially (roots order, count of an empty vocabulary, a third-layer port leading on, a line across layers, a port's count), restore; run only this phase's tests; commit
- [x] T021 Whitelist the explorer's settings for the pages `events` and `events-all` in `maxitor/web/model/rooms/pages.py`, with cases in `tests/test_rooms_pages.py`

## Phase 3: Filters and paint (one commit)

- [x] T022 [US4] Generalize `client/src/components/ui/ErdFilterPanel/ErdFilterPanel.tsx` to take `sections: { id, title, rows, paints }[]`, keeping its present props as a wrapper so ERD, Use case and the map are unchanged; titles on one line; the gear shift takes one point per painting section and opens the section moved to; update its README and tests
- [x] T023 [US4] In `client/src/lib/eventsExplorer.ts`: the sections of FR-016 by mode and by the screen as it would be with every row on; `off` keys `<section>:<row>`; Coverage only in Domains mode; a method kind off removes its `emits`; rows dimmed when nothing of them is on the screen (FR-017)
- [x] T024 [US4] Paint in the viewer per FR-018: Domains, Coverage, Events, Methods (strip of kinds, a single kind's colour on frame and icon), Actions; everything else grey; the domains paint when the painting section leaves
- [x] T025 [US4] Add tests: sections offered at each step of quickstart.md, a section kept when its rows hide all, filters applied to ports' numbers, every paint differing from every other in each mode (SC-004), ERD's panel unchanged in `client/src/components/ui/ErdFilterPanel/ErdFilterPanel.test.tsx`
- [x] T026 Break adversarially (a section offered from the filtered screen, a paint leaving nodes uncoloured, Coverage applied in Events mode), restore; run only this phase's tests; commit

## Phase 4: Comparison and state (one commit)

- [x] T027 [US5] In `client/src/lib/eventsExplorer.ts`: `loadExplorerDiff` merging A and B by id (B's where both) and marking nodes and pairs from `compareVersions()`; an event with a changed field marked changed; change counts per status behind each closed port (nodes behind plus links it would draw)
- [x] T028 [US5] In the viewer: marks as other diagrams, the change counts on closed ports ("+1 −1", kinds present only), counts on the version button, Side by side drawing each half's part with `drawnOn` (FR-023); no step-by-step through changes: the steps of the Graphviz diagrams walk drawn cells, while here a change behind a closed port is counted on the port
- [x] T029 [US5] Page settings `mode`, `layout`, `domains`, `off`, `opened`, `paint`, `paint_diff`, `disabled_changes` through `usePageSetting` in the viewer, read back from the address (FR-024); the room whitelist came in phase 2 (T021)
- [x] T030 Keep the explorer's pages in `client/scripts/check-layout-determinism.ts`: it walks the `events_all` and `events_domain` rows of the sidebar, and the explorer carries `data-layout-hash` of Graphviz's answer (since phase 2)
- [x] T031 [US5] Add tests: a pair from `explorer_graph()` / `explorer_graph_b()` showing the event and the link added from the first layer (SC-005), port change counts, the room whitelist accepting and refusing values, an address read back giving the same nodes, ports, filters and paint (SC-006)
- [x] T032 Break adversarially (a change behind a port not counted, a setting refused by the room), restore; run only this phase's tests; run quickstart.md on a stand serving both versions of the test graph; commit

## Converge

- [x] T036 [US2] Bring what a port opened into view by moving the picture only as far as it takes, and zoom out only when it does not fit, in `client/src/components/diagrams/EventsExplorer/EventsExplorer.tsx` (FR-022): centring it moved the clicked node 338 px on the stand

- [x] T037 [US1] Keep a workspace notice below the mode pill, as far from it as the pill is from the top (FR-002): the pill reserves the top centre in `client/src/lib/topCentre.ts`, `client/src/rooms/RoomBar/RoomBanner.tsx` stands below it, with `client/src/lib/topCentre.test.tsx`

- [x] T038 Drag the version handle of One from point to point and choose where it is let go, as each handle of Diff, in `client/src/components/history/VersionTrack/VersionTrack.tsx`, with `oneDrag.test.tsx` and its README (asked for by the maintainer on this branch)

## Phase 5: Closing check run (one commit if it changes anything)

- [x] T033 Take every check this machine can run to zero before the pull request (constitution VI.1): `bash scripts/run_checks_with_log.sh` passed, its one remark (Pylint on the demo's untracked builder) fixed there; then CI's closing check run on the pull request, and the browsers through `bash scripts/check_before_pr.sh` on the pushed commit

## Phase 6: Documentation (one commit)

- [x] T034 Rewrite the Events paragraph of `docs/tutorials/step-29-maxitor.md` for the explorer: modes, ports by layer, joining ports, filters and paint, Diff on ports

## Phase 7: Changelog (one commit)

- [x] T035 Raise `packages/maxitor/web/version.toml` (minor, 1.8.0) and `maxitor` in `packages/maxitor/pyproject.toml` (minor, 3.11.0), above what `main` reached meanwhile, refresh `uv.lock`; write one article in `packages/maxitor/CHANGELOG.md` under Unreleased: the explorer replaces the Events diagrams

## Dependencies

Phase 1 → 2 → 3 → 4 → 5 → 6 → 7. Phase 3 needs the screen of phase 2; phase 4 needs the sections of phase 3 (Changes is one more section). Inside a phase, tasks marked [P] touch different files.

## Implementation strategy

The MVP is phases 1–2: the explorer with ports in all three modes. Phases 3 and 4 complete the spec; nothing is pushed before phase 7.
