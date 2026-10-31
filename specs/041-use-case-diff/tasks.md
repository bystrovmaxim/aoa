# Tasks: Maxitor Compares Two Versions on Use-Case Diagrams

**Input**: `specs/041-use-case-diff/` (spec, plan, research, data-model, contracts, quickstart)

**Tests**: included: the project's rule is that a change ships with tests, and adversarial breaks are part of verification.

Each phase is one commit, made only on the maintainer's word. Phase 6 is three commits, in order (Principle VI).

## Phase 1: The server says what changed inside (blocks all)

- [X] T001 Add the facts to the issue: add this plan's phases 1, 4 and 5 to issue #292's body through `gh issue edit`, after checking the body file is non-empty, and fix its stale step numbers
- [X] T002 [P] Write the walk's tests in packages/maxitor/core/graph_compare/tests/test_changed_inside.py: a new, changed and removed result field; params; an aspect; a checker under an aspect; a `@connection` link; a `domain` link; a shared `Result`; an `entity_schema` target not entered; drawn edges not counted; an added and a removed action left out; a cycle; defined order
- [X] T003 Write `changed_inside(older, newer, comparison)` in packages/maxitor/core/graph_compare/src/maxitor/graph_compare/changed_inside.py and export it from `__init__.py`: the rule of research R1, the shapes of data-model ChangedPart and ChangedInside
- [X] T004 Hold the answer per pair in packages/maxitor/front/src/maxitor/front/model/diagrams/resources/comparison_store.py: `changed_inside()` beside `current()`, computed once, with a speed bound added to packages/maxitor/core/graph_compare/tests/test_graph_compare_speed.py
- [X] T005 Add `ChangedInsideAction` in packages/maxitor/front/src/maxitor/front/model/diagrams/actions/changed_inside_action.py and its route in packages/maxitor/front/src/maxitor/front/api/app.py, per contracts/maxitor-api.md, with tests in packages/maxitor/front/tests/test_changed_inside_read.py, keys and refusals included
- [X] T006 Give every link its protocol `id` in packages/maxitor/front/src/maxitor/front/model/diagrams/actions/domain_use_case_diagram_action.py and its schema, with a test that each id exists in the graph file
- [X] T007 Extend the stand: .demo-history/build_erd_full.py with the versions the spec's stand section lists (out of git); rebuild; read the new endpoint for each new pair
- [X] T008 Adversarial: ignore `generic:result`, then enter `entity_schema`, then count a drawn edge; each time the matching test fails and no other; restore

## Phase 2: Marks and counts (US1, US2)

**Independent test**: a pair with only a result field changed: one amber action, the button `+0 −0 ~1`.

- [X] T009 [P] [US1] Write tests in packages/maxitor/front/client/src/lib/useCaseDiff.test.ts: union of two diagrams, one side empty, A's order independent, statuses, changed inside, added stands over inside, counts, nothing changed
- [X] T010 [US1] Write packages/maxitor/front/client/src/lib/useCaseDiff.ts: `mergeUseCaseDiagrams`, `markUseCaseDiagram`, `useCaseCounts`, sorted by id per data-model
- [X] T011 [US1] Add `compareChangedInside` to packages/maxitor/front/client/src/api/compare.ts, and the diagram read for version A in packages/maxitor/front/client/src/api/domainUseCaseDiagram.ts, an unknown domain answering empty
- [X] T012 [US1] Draw marks in packages/maxitor/front/client/src/lib/buildDomainUseCaseDotSource.ts: colours from `MARK_LOOK`, removed dashed, unchanged faded, the sign in the tooltip; no change to the DOT in One, proven by a test
- [X] T013 [US1] Wire Diff in packages/maxitor/front/client/src/components/diagrams/UseCaseDiagramViewer/UseCaseDiagramViewer.tsx: load both, follow Live, `setDiffCounts`, "no changes" drawn as One; update its README
- [X] T014 [US2] Prove on packages/maxitor/front/client/src/lib/useCaseDiff.test.ts that a shared `Result` marks each action, and in the browser that the ERD and the map mark the same pair as before (SC-005)
- [X] T015 [US1] Check the left panel's `+` and `−` pages open a domain only in A or B, in packages/maxitor/front/client/src/lib/sidebarDiff.ts; fix if they do not
- [X] T016 [US1] Walk User Stories 1 and 2 on `erd-full` in every layout mode; adversarial: drop a mark, confirm the test fails, restore

## Phase 3: The card (US3)

**Independent test**: click each kind of element and compare with the read.

- [X] T017 [P] [US3] Test grouped parts in packages/maxitor/front/client/src/components/history/DiffCard/DiffCard.test.tsx
- [X] T018 [US3] Add optional `parts` to `CardTarget` in packages/maxitor/front/client/src/lib/erdDiffCard.ts and render them in packages/maxitor/front/client/src/components/history/DiffCard/DiffCard.tsx: the line "The action is the same; its parts changed", `diff-part-group` groups, own differences above them; the ERD's card unchanged
- [X] T019 [US3] Open the card from a click in packages/maxitor/front/client/src/components/diagrams/UseCaseDiagramViewer/UseCaseDiagramViewer.tsx; close by Escape, click outside, Live; update DiffCard's README
- [X] T020 [US3] Walk User Story 3 on `erd-full`; adversarial: drop one group, the test fails, restore

## Phase 4: The stepper (US4)

- [X] T021 [US4] Extract the stepping logic of packages/maxitor/front/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx into packages/maxitor/front/client/src/lib/useGraphvizChangeStepping.ts, the ERD's behaviour unchanged (research R6)
- [X] T022 [P] [US4] Test `useCaseChanges` in packages/maxitor/front/client/src/lib/useCaseDiff.test.ts: order, links included, each once
- [X] T023 [US4] Write `useCaseChanges` in packages/maxitor/front/client/src/lib/useCaseDiff.ts and use the hook in UseCaseDiagramViewer.tsx; Graphviz element ids as cells; a link steps with no card
- [X] T024 [US4] Walk the stepper with keys, the list and a room on `erd-full`, the ERD's again; adversarial: skip links, the test fails, restore

## Phase 5: The filter panel (US4)

- [X] T025 [US4] Let packages/maxitor/front/client/src/components/ui/ErdFilterPanel/ErdFilterPanel.tsx go without a kinds section, with a test in ErdFilterPanel.test.tsx
- [X] T026 [P] [US4] Test the Changes filter in packages/maxitor/front/client/src/lib/useCaseDiff.test.ts: counts, stepper and "no changes" follow
- [X] T027 [US4] Replace the domain legend in UseCaseDiagramViewer.tsx with the panel, Changes in Diff, the gear shift, settings in the address and the room, One's paint and Diff's apart; extend packages/maxitor/front/client/src/lib/filterUseCaseDiagramByDomains.ts
- [X] T028 [US4] Walk the panel on `erd-full`, phone width and a room; a card whose element is hidden closes; adversarial: count before filtering, the test fails, restore

## Phase 6: The closing three (Principle VI)

- [ ] T029 Closing check run: `bash scripts/run_checks_with_log.sh` taken to zero
- [ ] T030 Documentation: docs/how-to/compare-two-versions.md, docs/tutorials/step-26-maxitor.md, examples/step_26_maxitor/19_changed_inside.py and its notebook, every case, run while written; the Russian draft docs/how-to/compare-two-versions.ru_draft.md beside the page
- [ ] T031 Changelog: one article in docs/CHANGELOG.md

## Dependencies

Phase 1 blocks all. 2 needs 1; 3 needs 2; 4 needs 3; 5 needs 4 (the list follows filters); 6 is last. [P] tasks are tests that touch their own file.

## Strategy

The whole picture ships together; the order follows dependencies alone. T007's stand is what each walk runs on.
