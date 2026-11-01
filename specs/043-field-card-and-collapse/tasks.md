# Tasks: Maxitor: One Card on Hover, and Tables That Collapse

**Input**: Design documents from `specs/043-field-card-and-collapse/`

**Tests**: Included: every behaviour gets a test that a break makes fail. C = `packages/maxitor/front/client/src`, S = `packages/maxitor/front`.

**Commits**: Only on the maintainer's word (Principle I). The card's phases 2–5 share files with collapsing's wiring, so they land together; the protocol and the means to collapse land before them.

## Phase 1: The specification (commit 1)

- [x] T001 Write spec, plan, research, data model, contracts, quickstart, tasks

## Phase 2: US1 — One card for every field (commit 2) 🎯 MVP

- [x] T002 [US1] Add `GetElementCardAction` and its route in S`/src/maxitor/front/model/diagrams/actions/get_element_card_action.py`; test in S`/tests/`
- [x] T003 [US1] Add `lifecycle_id` to `list_entities_action.py` and to the query's test
- [x] T004 [US1] Create C`/api/elementCard.ts`, C`/lib/useHoverCard.ts` and C`/components/diagrams/ElementCard/`, sharing `DiffCard`'s body; test delay, stay and late answers
- [x] T005 [US1] `useGraphvizFocus`: no label where a card stands, one path for own and followed hover; test
- [x] T006 [US1] Wire the ERD: subject of a row and a header, table's field list, stepper card has priority
- [x] T007 [US1] `bindNameCopy` on every name, none by touch; remove the ERD's click card; a tap opens the card; test
- [x] T008 [US1] Adversarial breaks; walk quickstart 1–3, 7, 8

## Phase 3: US2 — The lifecycle miniature (commit 3)

- [x] T009 [US2] Create C`/lib/lifecycleMiniature.ts` (read, draw, keep) and `LifecycleMiniature`; test that a second call reads nothing
- [x] T010 [US2] Show it for `lifecycle_id`; a click opens the full diagram; walk quickstart 4

## Phase 4: US2 — Changes in the miniature (commit 4)

- [x] T011 [US2] Read through `loadLifecycleDiff` in Diff, key by pair; test; walk quickstart 5

## Phase 5: US3 — The card on the full graph (commit 5)

- [x] T012 [US3] `MapEngine`: raise the hover for real nodes and links, keep bundles, centres and clicks (FR-012a); follow it
- [x] T013 [US3] Wire `MapViewer`; test; walk quickstart 6

## Phase 6: US4 — Collapse one table (commit 6)

- [x] T014 [US4] Create C`/lib/erdCollapse.ts`; test each row kind, marks, lines
- [x] T015 [US4] `buildDotSource`: rows, stable indices, control, hidden count; test; everything expanded equals the old rows (FR-031)
- [x] T016 [US4] Two page settings in C`/lib/viewUrl.ts`; test
- [x] T017 [US4] The control's click, the header kept on screen; the card lists all fields; walk quickstart 9, 11

## Phase 7: US5 — Collapse all, and the layout check (commit 7)

- [x] T018 [US5] Toolbar button; a table arriving later; test
- [x] T019 [US5] A collapsed page in `check-layout-determinism.ts`; walk quickstart 10

## Added on the stand, at the maintainer's word

- [x] T023 Protocol 1.2: descriptions of entity fields, lifecycles, roles and `@connection` reach the graph
- [x] T024 A table's card lists names, its fields open from one control, the choice remembered; the pointed field's type and description below; its lifecycle's picture stays bright
- [x] T025 The card of a line; white labels; one status disk everywhere, with `=` for unchanged; toolbar icons
- [x] T026 From afar a table's card opens anywhere on it; a table that changed domain counts as changed
- [x] T027 A card goes round related tables, active lines and labels; a follower gets the open card itself, its inside and its spot on the diagram; the list's pointed row too
- [x] T028 `scripts/cardMechanics.ts`: the card and collapsing with a real mouse, in the check run

## Phase 8: Closing check run (commit 8)

- [x] T020 `bash scripts/run_checks_with_log.sh` to zero

## Phase 9: Documentation (commit 9)

- [x] T021 Update Maxitor's docs and component READMEs, with a Russian draft

## Phase 10: Changelog (commit 10)

- [x] T022 One article in `docs/CHANGELOG.md`
