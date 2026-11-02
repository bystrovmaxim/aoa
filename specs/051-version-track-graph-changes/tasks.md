# Tasks: The version track shows where the graph changed

**Input**: Design documents from `specs/051-version-track-graph-changes/`

**Tests**: included, because every behaviour here protects a rule of the issue. Each phase is one commit, and after it only its own tests run.

Paths are relative to `packages/maxitor/web/` unless they start at the repository root.

## Phase 1: The server carries the version file (commit 1)

**Purpose**: every later phase reads these fields.

- [X] T001 Accept `version_link=` and `version_key=` on a public address, with the refusals of `contracts/history-routes.md`, in `maxitor/web/model/core/history_address.py` and `client/src/lib/historyAddress.ts`, and name them in `version_source` and `parse_version_source`
- [X] T002 Pass `version_link` and `version_key` through `describe` and `versions` in `maxitor/web/model/core/resources/repo_graph_port_gateway.py`, and from `check_version_access_action.py`
- [X] T003 Add `version_file`, `version_problem`, `version_link`, `version_key` to `maxitor/web/model/core/history_entry.py`, filled in `history_reading.py`
- [X] T004 Return `version_file` and `version_problem` from `actions/open_history_action.py` and `actions/history_versions_action.py`, after reading how `history_versions_action.py` makes its tag, and refresh them in `actions/check_history_action.py` also on a `304`, counting a change like a change of Live and in the tag a polling tab receives
- [X] T005 Teach `tests/fixtures/stand_in_port.py` the two parameters and fields, and add `tests/test_history_version_file.py`: both reach the port on all three requests, both fields reach the reader, a problem appearing on a `304` reaches a polling tab, and the same link with two version files gives two histories
- [X] T006 Extend `client/src/lib/historyAddress.test.ts` with the accepted and refused addresses

**Adversarial break**: drop `version_key` from the list request; only its test fails.

---

## Phase 2: User Story 1 - Points and numbers (commit 2) 🎯 MVP

**Goal**: a large point means the graph changed; the number comes from the file.

**Independent Test**: a history with a version file shows small points with numbers where only the version rose.

- [X] T007 [US1] Add `graph_changed`, `version`, `version_changed` to `HistoryVersion`, and `version_file`, `version_problem` to the opened and polled answers, in `client/src/api/history.ts`, kept on the opened history in `client/src/app/useOpenHistory.ts`
- [X] T008 [US1] Give `numbersOf` and `shownNameOf` a `versionFile` argument: with a file, the number is the point's `version`, otherwise the last tag, in `client/src/lib/versionNames.ts`, with the callers in `client/src/app/App.tsx` and `client/src/components/history/VersionsBetween/VersionsBetween.tsx`
- [X] T009 [US1] Replace `Point.release` by `large` and `named` as in `data-model.md`, and draw size and names from them, in `client/src/components/history/VersionTrack/VersionTrack.tsx`, passing `versionFile` from `VersionPicker.tsx`
- [X] T010 [US1] Cover the four acceptance scenarios, a point with no `graph_changed` and a point with an empty `version` in `client/src/lib/versionNames.test.ts` and `client/src/components/history/VersionTrack/trackLooks.test.tsx`, updating what they assert about release size

**Adversarial break**: draw size from a flag instead of `graph_changed`; only the size test fails.

---

## Phase 3: User Story 3 - A problem in plain words (commit 3)

**Goal**: a version problem is read, not guessed.

**Independent Test**: a history with `version_problem` opens its graph and shows the sentence.

- [X] T011 [US3] Show `version_problem` at the foot of `client/src/components/history/VersionPicker/VersionPicker.tsx`, and as a scarlet dot with the same text on `client/src/components/history/VersionButton/VersionButton.tsx`
- [X] T012 [US3] Test both in `VersionPicker.test.tsx` and `VersionButton.test.tsx` next to those components, and that a history with no problem shows neither

**Adversarial break**: drop the problem from the polled answer's use on the client; only its test fails.

---

## Phase 4: User Story 2 - The icon (commit 4)

**Goal**: a viewer hides the points that did not change the graph, and nothing chosen moves.

**Independent Test**: choose a small point, untick the checkbox, and compare what is chosen.

- [X] T013 [US2] Add `client/src/lib/smallPointsShown.ts` following `lib/hoverCardsOn.ts`: default shown, guarded storage
- [X] T014 [US2] Add the three-point icon with a tooltip beside the "i" in `client/src/components/history/VersionPicker/VersionPicker.tsx`, only where a point did not change the graph
- [X] T015 [US2] Filter in `layOut` after names and numbers are built, as in research R5, keeping the chosen point, both ends and the followed drag, in `client/src/components/history/VersionTrack/VersionTrack.tsx`
- [X] T016 [US2] Carry the flags of hidden points as in research R6, drawn in `VersionTrack.tsx` and listed in `VersionTip.tsx`
- [X] T017 [US2] Test in `client/src/components/history/VersionTrack/hiddenPoints.test.tsx`: chosen and range unchanged, a hidden point stays while chosen and leaves after, a follower keeps the followed point, names unchanged, flags moved and listed, the earliest point takes flags with nothing before it, nothing goes to a room or the address

**Adversarial break**: let hiding clear the chosen point; only the test that hiding keeps it fails.

---

## Phase 5: User Story 3 - Two points with one graph (commit 5)

**Goal**: a comparison of equal graphs says so.

**Independent Test**: put both handles either side of a small point.

- [X] T018 [US3] Add `sameGraph` to `client/src/lib/versionRange.ts` as in research R7, with tests in `client/src/lib/versionRange.test.ts`
- [X] T019 [US3] Say "Both versions have the same graph" in `client/src/components/history/VersionPicker/VersionPicker.tsx`, and use it for the counts of `VersionButton.tsx`, with tests next to them

**Adversarial break**: count the older end as part of the stretch in `sameGraph`; only its test fails.

---

## Phase 6: User Story 4 - The legend (commit 6)

- [X] T020 [US4] Rewrite "Size", add small points and the icon, in `client/src/components/history/VersionPicker/TrackLegend.tsx`, with `TrackLegend.test.tsx` and the READMEs of `VersionTrack` and `VersionPicker`

---

## Phase 7: Long history and the stand (commit 7)

- [X] T021 Extend `client/src/components/history/VersionTrack/longHistory.test.tsx` to 500 points, half of them small, with choosing and toggling inside one second
- [X] T022 Extend the local history `erd-full` with a version file and one broken history, start the stand, walk `quickstart.md` in the browser and show the result to the maintainer
- [X] T026 Raise the versions the change needs in `packages/maxitor/web/version.toml`, `packages/maxitor/pyproject.toml`, root `version.toml` if the gate asks, and `uv.lock`

---

## Phase 8: The tail (one commit each)

- [ ] T023 The closing check run: `bash scripts/check_before_pr.sh` on the pushed commit and CI's run, every remark fixed
- [ ] T024 The documentation: every case as a script and a notebook, `examples/step_26_maxitor/23_version_track.py` and `.ipynb` at the repository root, executed, with the tutorial and how-to pages under `docs/`
- [ ] T025 The changelog: one article at the top of `docs/CHANGELOG.md`

---

## Dependencies & Execution Order

Phase 1 comes first. Phase 2 needs it. Phases 3, 4 and 5 need Phase 2 and touch `VersionPicker.tsx`, so they run in order. Phase 6 needs 4. Phase 7 needs all of them. The tail goes last, in its order.

## Parallel Example

T005 and T006 can run together; so can T010 once T008 and T009 stand. Everything else shares a file with its neighbour.

## Implementation Strategy

Phases 1 and 2 are the smallest result a reader can see. Corrections of look go on the stand without tests or check runs until the look is accepted.
