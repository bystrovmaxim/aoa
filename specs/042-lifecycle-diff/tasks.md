# Tasks: Maxitor Compares Two Versions on Lifecycle Diagrams

**Input**: Design documents from `specs/042-lifecycle-diff/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included: the house rule is adversarial verification, so every behaviour gets a test that a break makes fail. C = `packages/maxitor/front/client/src`, S = `packages/maxitor/front`.

**Commits**: One phase, one commit, each only on the maintainer's word (Principle I). A commit references #293.

## Preparation: the stand (out of git, not a phase)

- [x] T001 Append versions to `.demo-history/build_erd_full.py` on Inventory's lifecycles, after the last one, so that existing commits stay: every case of spec "The acceptance stand"; run it and refresh `.demo-history/erd-full.url`

## Preparation: the ids (land in phase 1's commit)

- [x] T002 Add `id` to each state and each transition, read from the graph, in S`/src/maxitor/front/model/diagrams/actions/get_lifecycle_finite_automaton_action.py` and `get_lifecycle_finite_automaton_action_schema.py`, per `contracts/maxitor-api.md`
- [x] T003 Test both ids and an unchanged remainder of the answer in S`/tests/test_get_lifecycle_finite_automaton_action.py`
- [x] T004 Add `id` and `diff?` to the wire types in C`/model/lifecycleFiniteAutomaton.ts`; let `fetchLifecycleFiniteAutomaton` take a read (research R2) in C`/api/lifecycleFiniteAutomaton.ts`

## Phase 1: US1 + US2 — Statuses, counts, left panel (commit 1) 🎯 MVP

**Goal**: Every state and transition marked, the button counting them, a lifecycle of one version opening, `~` on a changed row.

**Independent Test**: On the stand, every mark equals the comparison and the button equals the marks; `+` and `−` rows open, all green, all red.

- [x] T005 [US1] Create C`/lib/lifecycleDiff.ts`: `mergeLifecycles`, `markLifecycle`, entry and exit statuses (research R5), `lifecycleCounts`, `unmarkedLifecycle`, `loadLifecycleDiff` (research R2)
- [x] T006 [US1] Test in C`/lib/lifecycleDiff.test.ts`: union by id, B's label and kind, one version only, two transitions into one state, a moved transition as removal plus addition, a change of order alone, dots never counted
- [x] T007 [US1] Draw marks in C`/lib/buildLifecycleFsmDotSource.ts`: colours of `MARK_LOOK`, removed dashed, sign in the label, a final state still final, unchanged grey and dim, declared colour ignored in Diff; `id=` on transitions in Diff only; sorted so a pair gives one text
- [x] T008 [US1] Test in C`/lib/buildLifecycleFsmDotSource.test.ts`: One's text equals a recorded text byte for byte (FR-030); each status's attributes
- [x] T009 [US1] Wire Diff into C`/components/diagrams/LifecycleFsmViewer/LifecycleFsmViewer.tsx`: load, `setDiffCounts`, "no changes" through `nothingChanged`, following Live through `enabledKeys`, both directions
- [x] T010 [US2] Add `changed` to `mergeSidebars` (research R8) in C`/lib/sidebarDiff.ts`, read the comparison in C`/components/navigation/LeftSidebar/hooks/useSidebarPayload.ts`, draw `~` in C`/components/navigation/LeftSidebar/LeftSidebar.tsx`; test in the sidebar's test files, the lifecycle node's own change marking nothing
- [x] T011 [US2] Message and way back for a lifecycle not in the shown version or pair (FR-028), and expanding the domain of a row of one version (FR-027), in the viewer and `LeftSidebar.tsx`
- [x] T012 [US1] Adversarial breaks, each failing only its test: status from position, a dot counted, colour kept in Diff, `~` from a bare prefix without the colon; on one pair of the stand the ERD's and the use-case diagram's marks are the same as on `main` (FR-031)
- [ ] T013 [US1] Walk quickstart 1–5, 10, 11 on the stand; on the maintainer's word commit 1

## Phase 2: US3 + stepper — The card and the walk (commit 2)

**Goal**: A click tells what changed; the stepper reaches every change.

**Independent Test**: Quickstart 6 and 7.

- [x] T014 [US3] Add `lifecycleCard`, `lifecycleIdAt` to C`/lib/lifecycleDiff.ts`: a transition named by the display names of its two states, a kind's change in plain words; tests in C`/lib/lifecycleDiff.test.ts`
- [x] T015 [US3] Mount `DiffCard` in `LifecycleFsmViewer.tsx`: click, outside, Escape, following Live, unchanged as in One, names never ids
- [x] T016 [US4] Add `lifecycleChanges` to C`/lib/lifecycleDiff.ts` (order in data-model.md); test each change exactly once, whatever is in view
- [x] T017 [US4] Mount `useGraphvizChangeStepping` in `LifecycleFsmViewer.tsx`: stepper, list, Shift + ↑ ↓, legend, a room's follower
- [ ] T018 [US3] Adversarial breaks, walk, on the maintainer's word commit 2

## Phase 3: US4 — Panel, paint, hover (commit 3)

**Goal**: The diagram narrows and traces as the use-case diagram does.

**Independent Test**: Quickstart 8 and 9.

- [x] T019 [US4] Add `lifecycleChangeKinds`, `filterLifecycleByChanges`, `filterLifecycleByKinds`, `withLifecycleOneHop` to C`/lib/lifecycleDiff.ts`, with tests: a state's transitions leave with it
- [x] T020 [US4] Mount `ErdFilterPanel` and `OneHopToggle` in `LifecycleFsmViewer.tsx`: Elements and, in Diff, Changes; gear shift on Elements in One, on Changes in Diff; counts follow; a card of a hidden element closes; defaults stay out of the address
- [x] T021 [US4] Call `bindUseCaseHover` in `LifecycleFsmViewer.tsx`, in One and Diff, kept with `useGraphvizFocus`
- [x] T022 [US4] Update C`/components/diagrams/LifecycleFsmViewer/README.md`; check One's address and DOT on an untouched page
- [ ] T023 [US4] Adversarial breaks, walk in a room and at phone width, on the maintainer's word commit 3

## Phase 4: Closing (three commits, in this order)

- [x] T023a Run `/speckit-converge` and do what it adds, before the check run
- [x] T024 Closing check run taken to zero: `scripts/run_checks_with_log.sh` (commit)
- [x] T025 Documentation: the page, every case as a runnable script and a notebook, its `.ru_draft.md` beside it (commit)
- [x] T026 Changelog: one article in `packages/maxitor/CHANGELOG.md`, and the Russian draft (commit)

## Dependencies

Preparation first, then phases 1 → 2 → 3 → 4. T005 before T007 and T009. Parallel: T003 with T004; T010 with T007.

## Implementation Strategy

Phase 1 alone is the MVP: it delivers the issue's two criteria. The rest makes this diagram read like the others.
