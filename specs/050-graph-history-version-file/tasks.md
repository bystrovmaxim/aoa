# Tasks: A graph's history joined with its version file

**Input**: Design documents from `specs/050-graph-history-version-file/`

**Tests**: Included: the spec's scenarios and the quickstart's breaks need them.

**Paths**: `PORT` is `packages/maxitor/tools/repo_graph_port/maxitor/repo_graph_port`, and `TESTS` is `packages/maxitor/tools/repo_graph_port/tests`.

**One phase is one commit.** Versions are raised once, in phase 7, because `version-gate` compares the whole pull request.

## Phase 1: The cache knows the graph (US4, commit 1)

**Goal**: two graphs of one repository at one commit stay apart.

**Independent test**: read two graphs at one commit, in both orders, cold and warm.

- [X] T001 [US4] Add a test of two histories on different graph files at one commit, in both orders, cold and warm, in TESTS/test_versions.py
- [X] T002 [US4] Key graph bytes, facts and detail by repository, `graph_file` and commit under `graphs/<repository key>/<graph key>/`, in PORT/resources/version_cache.py
- [X] T003 [US4] Remove the old `versions/` folder when the cache opens, with a test that nothing old is served, in PORT/resources/version_cache.py
- [X] T004 [US4] Pass `history.graph_file` to every cache call in PORT/history_reading.py and PORT/actions/version_action.py

## Phase 2: Reading a number (commit 2)

**Goal**: one pure place reads a number and names what is wrong.

- [X] T005 Copy the sample files of `specs/001-version-toml-spec/samples` from `version-gate` `v0.1.1` into TESTS/fixtures/version_gate/
- [X] T006 Add tests for TOML, JSON, a dotted key, a missing key, a value that is not a string, a broken file, another format and `driver`, using those samples, in TESTS/test_version_source.py
- [X] T007 Create PORT/version_source.py: read a key by the file's extension, giving a number or a reason (`missing`, `not a string`, `broken`, `format`, `driver`), with no I/O

## Phase 3: Naming the second file (US2, commit 3)

**Goal**: a history can name its version file, its key and its old paths.

**Independent test**: configured and public histories carry the new fields.

- [X] T008 [US2] Add `version_file`, `version_key` (default `version`), `graph_file_before` and `version_file_before` to `History` in PORT/history.py
- [X] T009 [US2] Read and type-check the new keys in PORT/resources/histories_config.py, refusing a wrong type but not a wrong path
- [X] T010 [US2] Let `public_history` take `version_link` and `version_key` in PORT/history.py, and pass them through `chosen` in PORT/history_reading.py
- [X] T011 [US2] Add `version_link` and `version_key` to the parameters of PORT/actions/history_action.py, PORT/actions/describe_history_action.py and PORT/actions/version_action.py

## Phase 4: Points (US1, commit 4)

**Goal**: each point says what changed.

**Independent test**: a six-commit repository gives exactly the expected three values.

- [X] T012 [US1] Add scenario tests for User Story 1 and the edge cases on real repositories, including tags on a version-only point and a history with no version file returning the same points as before, in TESTS/test_versions.py
- [X] T013 [US1] Let `versions` take several paths, and add `first_file_at`, in PORT/resources/git_mirror.py
- [X] T014 [US1] Add the pure rules `graph_differs` (from `graph_change`, plus `schema_version`, and bytes for a file that is not a graph) and `join_points` to PORT/history_versions.py
- [X] T015 [US1] Add `graph_changed` (default true), `version` and `version_changed` (default false) to PORT/version_record.py
- [X] T016 [US1] Add `points_of`, keeping a number per repository, `version_file`, `version_key` and commit, in PORT/history_reading.py and PORT/resources/version_cache.py
- [X] T017 [US1] Give a version-only point the facts of the point before, an empty `change` and its contribution from git, reading no graph; a point that touched the graph compares with the previous commit that touched it, not the previous point, in PORT/history_reading.py
- [X] T018 [US1] Build the answer from `points_of` in PORT/actions/history_action.py, placing tags on all the points by today's rule (FR-014), with neutral values on open pull requests
- [X] T019 [US1] Open every point in PORT/actions/version_action.py
- [X] T020 [US1] Watch every path in all branches of PORT/actions/receive_host_event_action.py, and count points in PORT/actions/describe_history_action.py

## Phase 5: A bad link (US3, commit 5)

**Goal**: every bad link is explained and the graph stays open.

**Independent test**: each cause, in both answers.

- [X] T021 [US3] Add a test per cause, reading both answers, in TESTS/test_actions.py
- [X] T022 [US3] Add `version_problem_of`, checked at the head of the branch: the folder contains the graph, both files exist, the number reads, and `version_link` names the same repository and branch, in PORT/history_reading.py
- [X] T023 [US3] Add `version_problem` to the results of PORT/actions/history_action.py and PORT/actions/describe_history_action.py, and `version_file` to the second

## Phase 6: Moved folders (US5, commit 6)

**Goal**: a move keeps the history.

**Independent test**: a repository whose files moved mid-history.

- [X] T024 [US5] Add a test with old paths and one without in TESTS/test_versions.py
- [X] T025 [US5] Run the list over all old paths, and read each commit from the first path that exists there, in PORT/history_reading.py

## Phase 7: The versions (commit 7)

- [X] T026 Raise `packages/maxitor/pyproject.toml` to `3.1.0` and `packages/maxitor/tools/repo_graph_port/version.toml` to `1.1.0`

## Phase 8: The check run (commit 8)

- [X] T027 Make each break of quickstart.md, confirm its test fails and no other does, and restore
- [X] T028 Count the requests to the stand-in GitHub on a long history before and after, and keep the numbers for the pull request
- [X] T029 Run `bash scripts/run_checks_with_log.sh` and take every remark to zero; run `graph-builder write` if the port's graph changed

## Phase 9: The documentation (commit 9)

- [X] T030 Update packages/maxitor/tools/repo_graph_port/README.md and docs/how-to/run-the-repo-graph-port.md with the new keys, fields and causes
- [X] T031 Add a script and a notebook per case under examples/step_26_maxitor/, run them, and link them from docs/tutorials/step-26-maxitor.md

## Phase 10: The changelog (commit 10)

- [X] T032 Write one article at the top of docs/CHANGELOG.md

## Dependencies

- Phase 1 needs nothing. Phase 3 needs phase 2 only for the reasons it reports. Phase 4 needs 1, 2 and 3. Phases 5 and 6 need 4.
- The phases run in order, each one commit. Within a phase only the tests can run alongside.

## Strategy

The smallest useful result is phases 1 to 4. Phase 1 stands alone: it fixes a real fault even if the rest waits.
