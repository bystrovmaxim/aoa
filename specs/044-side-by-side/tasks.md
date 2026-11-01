# Tasks: Maxitor: Two Versions Side by Side, and Comparison in Rooms

**Input**: Design documents from `specs/044-side-by-side/`

**Tests**: Included: every behaviour gets a test that a break makes fail. C = `packages/maxitor/front/client/src`, S = `packages/maxitor/front/src/maxitor/front`, T = `packages/maxitor/front/tests`.

**Commits**: Only on the maintainer's word (Principle I). One phase, one commit.

## Phase 1: The specification (commit 1)

- [x] T001 Write spec, plan, research, data model, contracts, quickstart, tasks in `specs/044-side-by-side/`

## Phase 2: The half, with no visible change (commit 2)

**Goal**: everything per-tab becomes per-half where a half exists. One and Diff answer exactly as before.

- [x] T002 Create `HalfContext`, `useHalf` and the side projection in C`/lib/half.ts`, with `C/lib/half.test.ts`
- [x] T003 Let the map's readers take a half's read in C`/api/map.ts` and `mapEngine.ts`; the other diagrams read the pair once and project it, so their readers stay as they are (research R1)
- [x] T004 Map `layout` to `layout_a` / `layout_b` under a half in C`/lib/pageSettings.ts`; test; allow `layout_a`, `layout_b` and `selected` in `setting_error` in S`/model/rooms/`, with a test in T
- [x] T005 Register a surface per side, one surface outside Side by side, in C`/rooms/diagramSurface.ts`; test
- [x] T006 Keep `keptView` per side in C`/components/diagrams/MapViewer/mapEngine.ts`
- [x] T007 Let only half B write counts and steps in C`/lib/diffCounts.ts` and C`/lib/changeStepping.ts`; test
- [x] T008 Add `split` to the view in C`/app/useOpenHistory.ts`, C`/lib/urlState.ts`, C`/lib/viewUrl.ts`; `mode=split` without `a` opens One; test

## Phase 3: US1 — Two halves on the ERD (commit 3) 🎯 MVP

**Independent Test**: quickstart 1, 2, 6 on the ERD.

- [x] T009 [US1] Create C`/components/diagrams/SideBySide/` (`SideBySide.tsx`, `HalfHead.tsx`): two halves, each head with its version, layout mode and zoom, one filter panel for the workspace
- [x] T010 [US1] Render it from C`/app/App.tsx`'s workspace; a half that fails stands alone (FR-008); "Not in" for a whole diagram
- [x] T011 [US1] Enable the mode in C`/components/history/VersionPicker/VersionPicker.tsx` under Diff's rule; the top button says "side by side" with the counts
- [x] T012 [US1] Draw the projection in `ErdGraphvizCanvas.tsx`; test that a half's layout equals One's of that version (FR-002), and that an A half has no added element
- [x] T038 [US1] FR-041 by proof: `erdOfSide` is tested to stand each version as One stands it, and One is already held to one layout on every engine by `check-layout-determinism.ts`, which has no history to open a pair from
- [x] T013 [US1] Adversarial breaks; walk quickstart 1, 2, 6 on the stand

## Phase 4: US2 — One element across both, on the ERD (commit 4)

**Independent Test**: quickstart 3–5.

- [x] T014 [US2] Create C`/lib/selection.ts`: the `selected` setting, cleared by empty space and Escape; test
- [x] T015 [US2] Add `locate(ref)` to the surface, answering `in_view | moved | hidden | absent`, with its note in `SideBySide/HalfNote.tsx`; test each answer
- [x] T016 [US2] A click selects and copies, a press that moved does not, in C`/lib/erdCopy.ts` and the canvas; test
- [x] T017 [US2] Replay a half's hover on the other through C`/rooms/graphvizFocus.ts`, with no card from a replay (FR-015); test
- [x] T018 [US2] A step sets `selected`, the list being the pair's, in C`/lib/useGraphvizChangeStepping.ts`; test
- [x] T039 [US2] Keep a selected field visible in a collapsed table in C`/lib/erdCollapse.ts`; test
- [x] T019 [US2] Create `client/scripts/splitMechanics.ts` with a real mouse; it runs on a history by `SPLIT_URL`, since the check run opens a plain source with no two versions

## Phase 5: US1 + US2 — Use case and lifecycle (commit 5)

- [x] T020 [US1] Side projection and own layout in `UseCaseDiagramViewer.tsx` and C`/lib/buildDomainUseCaseDotSource.ts`; test
- [x] T021 [US1] The same in `LifecycleFsmViewer.tsx` and C`/lib/buildLifecycleFsmDotSource.ts`; test
- [ ] T022 [US2] Selection, locator and hover in both viewers; extend `splitMechanics.ts`; walk quickstart 1–5

## Phase 6: US1 + US2 — Full graph (commit 6)

- [x] T023 [US1] Two `MapEngine`s, half A starting after B has drawn, in `MapViewer.tsx`; test
- [x] T024 [US1] Marks by side: a version's own map carries none, so the pair's changes mark it by id in `mapEngine.ts`
- [x] T025 [US2] `locate`, click and followed hover in `mapEngine.ts`; extend `splitMechanics.ts`
- [x] T026 [US1] Walk the full graph in Side by side on the stand: two own layouts, hashes differ, no page error

## Phase 7: US3 — Phone (commit 7)

- [x] T027 [US3] A / B in place of Side by side at the `sm` breakpoint in `VersionPicker.tsx` and `SideBySide/`; a link opens on B; narrowing and widening; test
- [x] T028 [US3] Keep the selection centred across a flip, or say "Not in"; test; walk quickstart 7

## Phase 8: US4 — Rooms (commit 8)

**Independent Test**: quickstart 8.

- [x] T029 [US4] Add `Room.view` to S`/model/rooms/resources/room_registry.py`, `set_room_version_action.py`, `join_room_action.py` with the refusals of `contracts/room-protocol.md`; tests in T
- [x] T030 [US4] Relay `half` on `pointer`, `click`, `viewport`, dropping any other value, in `room_registry.py`; test
- [x] T031 [P] [US4] Add `sha_a` and `sha_b` to the comparison answer in S`/model/diagrams/`; test
- [x] T032 [US4] Carry `view` and `half` in C`/rooms/protocol.ts`, `connection.ts`, `useRoomSession.ts`, `usePointerSender.ts`, `PointerLayer`, `follow.ts`; test that zoom never passes and a follower's half pans
- [x] T033 [US4] The check of two pictures and both sha in C`/rooms/pageCheck.ts`, Diff included; test
- [x] T034 [US4] Adversarial breaks; walk quickstart 8 and 9 in two browsers

## Added on the stand, at the maintainer's word

- [x] T040 A change inside a table marks the table on both halves
- [x] T041 What has no pair puts the other half out, on a hover and on a selection
- [x] T042 Tracking: the other half's camera goes to what the pointer rests on, a switch each person holds
- [x] T044 On the full graph tracking takes the pointer half's zoom; a half's details carry the pair's marks, its filter the pair's rows, its steps the pair's place
- [x] T043 A lifecycle is part of its table: a change in it marks the table and its field, in Diff too

## Phase 9: Closing

- [ ] T035 Check run: `bash scripts/run_checks_with_log.sh` to zero (commit 9)
- [ ] T036 Documentation: `docs/how-to/compare-two-versions.md` and its `.ru_draft.md` (commit 10)
- [ ] T037 Changelog: one article in `docs/CHANGELOG.md` (commit 11)

## Dependencies

Phase 2 → 3 → 4 → 5 and 6 (in either order) → 7 → 8 → 9. T031 stands alone. Phases 5 and 6 repeat what 3 and 4 built, on other viewers, and touch different files.

## Parallel Example

T020 and T021 touch different viewers; T031 touches only the server's comparison.

## Implementation Strategy

Nothing is released before Phase 9: one pull request for #294. Order follows dependencies only.
