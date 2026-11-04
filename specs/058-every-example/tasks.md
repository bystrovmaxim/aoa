# Tasks: Every example in the documentation runs as it is written

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/example-checks.md](contracts/example-checks.md)

Each phase is one commit. Each phase brings a check together with the fixes it asks for, so it ends green. After a phase only its own tests run. Rows refer to the table "What is broken today" in issue #361.

## Phase 1: The harness and the removals

- [ ] T001 Dev extras `nbclient`, `ipykernel`, `pytest-xdist` in the root `pyproject.toml`; `uv lock`
- [ ] T002 `tests/examples/harness.py`: the pages in scope (research R9); the blocks of a page with their line, language, fragment reason (`# Fragment: <reason>.` on the first line, the reason non-empty) and shown output (R4); masking of values that differ on every run (R5); running a page's unmarked Python blocks in order in one process with each block's output captured (R3)
- [ ] T003 Tests of the harness itself: a fragment line is read, an empty reason is refused, a shown output is paired across a lead-in sentence ending with a colon and not across other prose, every kind of R5 value is masked, a later block sees an earlier block's names; in `tests/examples/test_harness.py`
- [ ] T004 Remove `examples/step_29_maxitor/` (every script and notebook) and every link to it in `docs/tutorials/step-29-maxitor.md` and the how-to pages (`compare-two-versions`, `read-a-diagram-without-zooming`, `open-a-graph-history`, `graph-setup`, `read-the-full-graph-map`); the pages keep their text (FR-014)
- [ ] T005 Remove `examples/step_24_relations/11_specialization_two_axes.{py,ipynb}`, its row in `docs/tutorials/step-24-relations.md`, and the claim that two axes through one reverse field work in `docs/reference/faq.md` and `docs/reference/intents-and-invariants.md` (FR-013)

## Phase 2: Every script runs (US1)

- [ ] T006 [US1] `tests/examples/test_examples_run.py`: no `_XFAIL_REASONS`; a folder with `__init__.py` is not a script (FR-002)
- [ ] T007 [P] [US1] Add `from aoa.action_machine.resources import Connections` to `examples/step_19_connections/14_fastapi_lifespan.py`, `15_mcp_call.py`, `16_pool_lifespan.py` (row 2)
- [ ] T008 [P] [US1] `examples/step_24_relations/72_role_dictionary.py`: compare the message without the version in its `errors.pydantic.dev` link (row 13)
- [ ] T009 [P] [US1] `examples/step_24_relations/67_cross_module_inverse.py`: import `inverse_model` relative to the script's folder; fix the run line of its docstring (rows 14, 15)
- [ ] T010 [US1] Every script of `examples/` except the LangGraph ones of Phase 3 exits 0

## Phase 3: LangGraph on `LangGraphController` (US1)

- [ ] T011 [US1] Read `packages/aoa-langgraph/src/aoa/langgraph/controller.py`: why a `@connection` to `LangGraphController` finds no graph node (`@exclude_graph_model`), and why `StubClassifyAction`'s `category` is still `UNSET` when the router reads it (rows 17, 18)
- [ ] T012 [US1] Fix the fault where it is: in the controller with a test in `packages/aoa-langgraph/tests/` and a raised version of `aoa-langgraph`, or in the examples `step_16_langgraph/01_external_connection.py` and `05_testing.py`
- [ ] T013 [P] [US1] Rewrite `examples/step_16_langgraph/01_langgraph.py` and `examples/extensions/02_langgraph.py` on `LangGraphController` (row 16)
- [ ] T014 [US1] `docs/tutorials/step-16-langgraph.md` and every page or README describes `LangGraphController` alone; `LangGraphAdapter` stays only in the changelogs (FR-012)
- [ ] T015 [US1] Every script of `examples/` exits 0, with no expected failure left

## Phase 4: Every notebook runs and gives its script's result (US1, US3)

- [ ] T016 [US1] `tests/examples/test_notebooks.py`: each notebook runs in a fresh kernel in its own folder with the install cell skipped; every line it prints is a line its script prints, in order, after masking (FR-003, FR-004); the first code cell is `!pip install …` and installs every module the notebook imports, mapped by one table in the test (R7, FR-011)
- [ ] T017 [US3] A first code cell `!pip install …` in every notebook of `examples/`, built from its imports by the table of T016
- [ ] T018 [P] [US1] Add the `Connections` import to the 44 notebooks of row 1
- [ ] T019 [P] [US1] Rows 3–9: adapter imports `aoa.fastapi` / `aoa.mcp`; `@compensate(charge_aspect, …)` in `research_self_knowledge/01_self_audit.ipynb`; the script's `Classifier(["first"])` in `step_24_relations/41_error_codes_not_literal.ipynb`; one import statement per cell in `how_to/02_custom_auth_coordinator.ipynb`; `await main()` instead of `asyncio.run(main())`; the repository root from `Path.cwd()`; `13_specialization_erd` reads its file from the root
- [ ] T020 [P] [US1] The notebooks follow every script fix of Phases 2 and 3; saved outputs that carry `errors.pydantic.dev/2.12` are regenerated
- [ ] T021 [US1] Every notebook runs and matches its script

## Phase 5: Every block of a page runs or says why not (US2)

- [ ] T022 [US2] `tests/examples/test_page_blocks.py`: every unmarked Python block runs after the earlier unmarked blocks of its page; a shown output equals what its block printed after masking (FR-005, FR-006)
- [ ] T023 [US2] Fix the blocks of rows 25–28: `domain=` on `@meta` in `README.md`; annotated aspect parameters in `packages/aoa-action-machine/README.md`; `aoa.fastapi` / `aoa.mcp` there; the `Connections` import in `docs/how-to/authoring-adapter.md`, `docs/tutorials/step-19-connections.md`, `docs/tutorials/step-21-resource.md`
- [ ] T024 [US2] For each of the other failing blocks (row 29): complete it if it is meant to run, or add `# Fragment: <reason>.` naming what it lacks
- [ ] T025 [US2] `docs/tutorials/step-23-dictionaries.md` and `docs/how-to/dictionary-references.md`: shown outputs match the installed Pydantic (row 13)
- [ ] T026 [US2] Every block of every page in scope runs or carries a fragment reason

## Phase 6: Every link to an example leads to it (US3)

- [ ] T027 [US3] `tests/examples/test_example_links.py`: every relative link to `examples/` resolves; every "Try in Colab" button is `https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/<path>.ipynb` with an existing `<path>` (FR-007, FR-008)
- [ ] T028 [US3] Replace the 30 Google Drive buttons, the 9 anchor buttons in `docs/extensions/jwt.md` and `docs/tutorials/step-14-fastapi.md`, and the 2 placeholders in `README.md` with the repository's Colab addresses (rows 22–24)
- [ ] T029 [US3] Every link and button resolves

## Phase 7: The checks run in CI (US4)

- [ ] T030 [US4] A step "Examples: scripts, notebooks, pages, links" in `scripts/check_run.py`: `uv run --extra dev pytest tests/examples -n auto`, also in CI's run (FR-010)
- [ ] T031 [US4] Tests of the new step in `tests/scripts/` beside the other check-run tests
- [ ] T032 [US4] Adversarial breaks from `quickstart.md`, each against the files of its phase: each fails and names the example; then restored

## Phase 8: The closing check run

- [ ] T033 `graph-builder check`, versions of every level that changed, `bash scripts/run_checks_with_log.sh` taken to zero; the constitution's principle VI.6 ("the closing check run does not execute them") put to the maintainer before the pull request opens

## Phase 9: Documentation

- [ ] T034 `docs/how-to/run-the-checks.md`: the new step, the fragment mark, the shown-output rule, the install cell and the Colab button, as a writer of a page needs them

## Phase 10: Changelog

- [ ] T035 One article in `docs/CHANGELOG.md`: every example now runs, what a fragment mark means, Colab opens the repository's notebooks, which examples were removed and why

## Dependencies

Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10. Phases 5 and 6 need only Phase 1 and could go earlier; they follow Phase 4 so that the notebooks a button opens already run.

## Parallel work

Inside a phase, the tasks marked [P] touch different files.

## Strategy

US1 first: the scripts and notebooks are what a reader runs most. The checks of US4 come last, once every check they run is green.
