---
description: "Tasks — check run: Radon as a real gate, one Ruff step, package builds confirmed"
---

# Tasks: Check run — Radon as a real gate, one Ruff step, package builds confirmed

**Input**: Design documents from `specs/046-check-run-gates/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/radon-gate.md, quickstart.md

**Tests**: Included. The contract lists every answer of the gate, and FR-011 requires each to be shown failing.

**Organization**: One phase = one commit (repository rule), except where a phase says otherwise. Phases follow the issue's order, as the plan decided, so User Story 3 comes first although it is P3. All stories are independent of each other.

**Commits**: Each commit waits for the maintainer's instruction (Principle I). "Commit point" below marks where one belongs; it does not authorize it.

**Paths**: Relative to the worktree `/Users/bystrovmaxim/PythonDev/aoa-issue-296`.

## Phase 1: Setup — times before any change

**Purpose**: The "before" numbers every phase's comment needs (FR-010). No commit.

- [X] T001 Record, on the untouched tree, the times of `task cc`, `task mi`, `bash scripts/check_before_commit.sh` and the full `bash scripts/run_checks_with_log.sh`, keeping them in `specs/046-check-run-gates/timings.ru_draft.md`

---

## Phase 2: User Story 3 — Package builds confirmed (Priority: P3)

**Goal**: The issue's claim about builds is settled with evidence. No code changes and no commit.

**Independent Test**: For all eight packages, the wheel and sdist member lists are the same between `uv build` and `python -m build`.

- [X] T002 [US3] Build the client, then each of the eight packages listed in `PACKAGES` in `scripts/check_run.py` both ways into a scratch directory outside the repository, per `specs/046-check-run-gates/quickstart.md`, recording both times
- [X] T003 [US3] Compare each wheel (`unzip -Z1`) and each sdist (`tar tzf`) file by file; report any difference to the maintainer with the package and the files (FR-009)
- [X] T004 [US3] Post the per-package table of files and times as a comment on issue #296, saying that #326 already made the change, and tick nothing until the maintainer agrees that this closes phase 1

**Checkpoint**: Phase 1 of the issue is closed by evidence.

---

## Phase 3: User Story 1 — A too-complex function stops the run (Priority: P1)

**Goal**: The two Radon steps can fail the run. Fixes go in first and the gate last, so the tree never fails its own check.

**Independent Test**: A function at complexity 21 fails `task cc` and names it; at 20 it passes. A grade-B module fails `task mi`.

### Simplifying what is over the limit

Every extracted helper is private, stays in its module and has a one-line docstring. Nothing else about the function changes.

- [X] T005 [P] [US1] Simplify `split_areas` to grade C by extracting the standing of the nodes and the cutting of edges in `packages/maxitor/core/graph_map/src/maxitor/graph_map/areas.py`
- [X] T006 [P] [US1] Simplify `assemble` to grade C by extracting one overview area and the bundles in `packages/maxitor/core/graph_map/src/maxitor/graph_map/assemble.py`
- [X] T007 [P] [US1] Simplify `_build_payload_from_duckdb` to grade C by extracting the row split and the node building in `packages/maxitor/front/src/maxitor/front/model/diagrams/actions/full_graph_action.py`
- [X] T008 [P] [US1] Simplify `_fill_database` to grade C with one helper per group of tables in `packages/maxitor/front/src/maxitor/front/model/diagrams/resources/duckdb_graph_resource.py`
- [X] T009 [P] [US1] Prove the test catches what it caught with one deliberate break, then simplify `test_examples_model_interchange_includes_parent_generalization_edges` to grade C keeping every assertion, and confirm the same break still fails it, in `packages/aoa-demo/tests/model/test_examples_generalization_edges.py`
- [X] T010 [P] [US1] Do the same for `test_no_line_is_missing_or_off_screen_for_any_view` in `packages/maxitor/front/tests/test_list_entities_lines_on_screen.py`
- [X] T011 [US1] Split `packages/maxitor/core/graph_map/tests/test_graph_map.py` into five modules by subject, areas, places, assembling, unions and marks, with `node`, `edge`, `document` and `by_id` in a helper module beside them; every test stays unchanged, and the test count before and after is the same. If a piece stays below grade A, except it under T014 with its reason
- [X] T012 [US1] Run each simplified package's tests and `uv run --extra dev radon cc packages/ -n D`; expect no function listed, and any function that cannot reasonably be simplified is reported to the maintainer before it is excepted

### The gate

- [X] T013 [US1] Write `tests/scripts/test_check_radon.py` covering every row of `specs/046-check-run-gates/contracts/radon-gate.md`, including complexity 20 passing and 21 failing, grade B and C failing the `mi` limit, all offenders listed, a method reported as `Class.method`, a stale exception, an exception with no reason, a Radon `error` entry, and empty or non-JSON output; confirm the tests fail before the gate exists
- [X] T014 [US1] Write `scripts/check_radon.py` per the contract and `data-model.md`: limits rank `D`, `E`, `F` for `cc` and rank `B`, `C` for `mi`; exception tables `(file, name) → reason` and `file → reason`, each "Must not be empty" for its reason and "Must be over the limit today"; all findings printed; a module header like its neighbours in `scripts/`
- [X] T015 [US1] Point the tasks `cc` and `mi` at the gate in `pyproject.toml`, keeping the step names and their rows in `scripts/check_run.py` untouched (FR-004)
- [X] T016 [US1] Adversarial proof: for each rule of the gate, break the rule in `scripts/check_radon.py`, confirm its test fails and no other does, restore (FR-011)
- [X] T017 [US1] Live proof per `quickstart.md`: a function made D-grade fails `task cc`, a module made B-grade fails `task mi`, and both are restored
- [X] T018 [US1] Run `bash scripts/check_before_commit.sh`, record the times of both steps after, and post the phase's comment on issue #296 with times before and after and the proofs

**Commit point**: Phase 2 of the issue, one commit.

---

## Phase 4: User Story 2 — One Ruff step (Priority: P2)

**Goal**: One Ruff row: it fixes locally and under `--fast`, and only reports in CI.

**Independent Test**: An unfixable error fails locally, a fixable one is fixed, and in the CI form a fixable one fails and stays in the file.

- [X] T019 [US2] In `tests/scripts/test_check_run.py`, add tests that the local, `--fast` and CI selections each hold exactly one Ruff row, that its command has `--fix` locally and under `--fast`, and that it has no `--fix` under `--where ci`; confirm they fail first
- [X] T020 [US2] In `scripts/check_run.py`, add the field `fast_keeps_command`, default `False`, to `Step` and honour it in `_select`; extend the `INVARIANTS` line of the class's AI-CORE block
- [X] T021 [US2] In `scripts/check_run.py`, set the `Ruff auto-fix` row to `home=BOTH`, `ci_command` to `uv run --extra dev ruff check packages/ tests/ scripts/`, `fast_keeps_command=True`; remove the `Ruff lint` row; update the comment above it and the module docstring where it describes the auto-fix
- [X] T022 [US2] Adversarial proof: remove `fast_keeps_command=True`, then the `ci_command`; confirm each is caught by its test and by no other; restore
- [X] T023 [US2] Live proof per `quickstart.md`: an unfixable error fails `check_before_commit.sh`; a fixable one is fixed and passes; a fixable one under `--where ci --skip-group packaging` fails with the file unchanged; restore
- [X] T024 [US2] Post the phase's comment on issue #296 with times before and after and the proofs from §4.2 of the issue

**Commit point**: Phase 3 of the issue, one commit.

---

## Phase 5: Closing

**Purpose**: The tail of Principle VI, in this order, one commit each. No task may absorb another. Plans stop at the changelog: no release, version or publishing work.

- [X] T025 Check run: run `bash scripts/run_checks_with_log.sh` and take every remark to zero, leaving only the two accepted ones; confirm wall time is no higher than T001's (SC-006). Afterwards restart `maxitor-client` if it was running
- [X] T026 Documentation: update `docs/how-to/run-the-checks.md`, removing "Ruff lint" from every table and sample, showing what each Radon step fails on with real output for each case of the contract, how an exception is added, and that the one Ruff step fixes locally and only reports in CI
- [ ] T027 Changelog: one plain article in `docs/CHANGELOG.md` about what this work created, with no technical detail and no per-file account

**Commit points**: Three commits, one per task.

**At the pull request**: The description says "Ruff lint" left the run, so the maintainer can change the list in `.specify/memory/constitution.md` (FR-013). The agent does not edit the constitution.

---

## Dependencies

- T001 goes first; everything else needs its numbers.
- US3 (T002–T004), US1 (T005–T018) and US2 (T019–T024) do not depend on each other. T025–T027 need all three.
- Inside US1: T005–T012 before T015, so the gate never goes on over a failing tree; T013 before T014, T014 before T015–T017.
- Inside US2: T019 before T020 and T021; T022 and T023 after them.

## Parallel Opportunities

- T005–T010 touch different files and can run side by side.
- T002 and T003 run per package, but the builds of `maxitor` wait for the client.

## Implementation Strategy

**Smallest useful result**: Phase 3 alone gives the repository its two real gates. Phases 2 and 4 stand on their own, and Phase 5 finishes the change, which is not finished without it.
