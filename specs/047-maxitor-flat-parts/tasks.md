---
description: "Tasks — Maxitor parts one level shallower, and front named web"
---

# Tasks: Maxitor parts one level shallower, and `front` named `web`

**Input**: Design documents from `specs/047-maxitor-flat-parts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/names.md, quickstart.md

**Organization**: one phase = one commit (repository rule). The four phases are the four phases of issue #305, and each carries its user-story labels. A phase ends at its checkpoint: show the diff and wait. The commit happens only on the maintainer's instruction (Principle I), and the issue's checkbox is ticked after the commit lands.

**Tests**: no new test files. The existing suites, the graph comparisons and the adversarial breaks are the proof. Each break is undone before the phase ends.

**Paths**: every path is relative to the worktree `/Users/bystrovmaxim/PythonDev/aoa-issue-305`.

## Phase 1: Move `front` (commit 1)

**Goal**: `front` holds its code at `front/maxitor/front/`, and nothing else changes.

**Independent test**: `check_before_commit.sh` green, `front/graph.json` the same by `cmp`.

- [x] T001 [US1] Take the baseline as in `specs/047-maxitor-flat-parts/quickstart.md`: `uv sync --all-extras`, copy `packages/maxitor/front/graph.json` and `packages/maxitor/tools/repo_graph_port/graph.json` to `/tmp/305-*.json`, and run `bash scripts/check_before_commit.sh` once, so any failure that exists before the work is known
- [x] T002 [US1] `git mv packages/maxitor/front/src/maxitor packages/maxitor/front/maxitor`, remove the empty `src/`, and rewrite line 1 of every moved module in `packages/maxitor/front/maxitor/front/` to its new path. Keep the rule "no `maxitor/__init__.py`"
- [x] T003 [US1] Update `packages/maxitor/pyproject.toml` for `front`: `only-include` to `front/maxitor`, `artifacts` to `front/maxitor/front/static/**/*`, `dev-mode-dirs` and the `sources` key to `front`
- [x] T004 [US1] Update `pyproject.toml` for `front`: `pythonpath` and `mypy_path` to `packages/maxitor/front`, the `typecheck` target to `packages/maxitor/front/maxitor` (not `packages/maxitor/front`, see research R3), and the vulture path to `packages/maxitor/front/maxitor`
- [x] T005 [P] [US1] Update `scripts/package_boundaries.toml` roots to `packages/maxitor/front/maxitor/front`, and `packages/maxitor/front/pytest.ini` to `pythonpath = .`
- [x] T006 [P] [US1] Update the `sys.path` entry in `packages/aoa-action-machine/tests/support/isolated_entity_models.py` to `packages/maxitor/front`
- [x] T007 [P] [US2] Update the client's build targets: `.gitignore` to `packages/maxitor/front/maxitor/front/static/`, the `COPY` target in `packages/maxitor/front/Dockerfile`, and `--outDir ../maxitor/front/static` in `.github/workflows/publish.yml`
- [x] T008 [P] [US2] Update `STATIC` and the `cp -R` text in `examples/step_26_maxitor/05_full_graph_in_the_browser.py` and `.ipynb`, and the paths in `docstring` line 11 of `packages/maxitor/front/maxitor/front/api/app.py`
- [x] T009 [US1] Run `uv sync --all-extras`, then `bash scripts/check_before_commit.sh` until green, and `cmp` both graph files against the baseline
- [x] T010 [US2] Build the client and the wheel as in quickstart, and confirm the count of `maxitor/front/static/` entries is above 0. Adversarial: restore the old `--outDir` value, confirm the wheel has none, then undo
- [x] T011 [US1] Adversarial: add `packages/maxitor/front/maxitor/__init__.py`, confirm that `pytest packages/maxitor/tools/graph_builder/tests/` or an import of a second part fails, then remove it. Adversarial: restore `pythonpath = src` in `packages/maxitor/front/pytest.ini` and run the part's tests. If the editable install hides the break, record that in the report and drop this break

**Checkpoint**: show the diff and wait for the commit instruction.

---

## Phase 2: Move the other four parts (commit 2)

**Goal**: all five parts are flat.

**Independent test**: `check_before_commit.sh` green, both graphs the same by `cmp`, `find` shows no `src/` but the client's.

- [x] T012 [US1] `git mv` `src/maxitor` to `maxitor` in `packages/maxitor/tools/graph_builder`, `packages/maxitor/tools/repo_graph_port`, `packages/maxitor/core/graph_compare` and `packages/maxitor/core/graph_map`, remove each empty `src/`, and rewrite line 1 of every moved module
- [x] T013 [US1] Update `packages/maxitor/pyproject.toml` for the four parts, and replace the comment "each part keeps its own ``src``"
- [x] T014 [US1] Update `pyproject.toml` for the four parts: `pythonpath`, `mypy_path`, `typecheck` targets ending at `/maxitor`, vulture paths, and the per-file ruff rule for `graph_builder`
- [x] T015 [P] [US1] Update `scripts/package_boundaries.toml` roots for the four parts, and `pythonpath = .` in `packages/maxitor/tools/graph_builder/pytest.ini`, `packages/maxitor/tools/repo_graph_port/pytest.ini`, `packages/maxitor/core/graph_compare/pytest.ini` and `packages/maxitor/core/graph_map/pytest.ini`
- [x] T016 [P] [US1] Update the three schema paths in `tests/scripts/test_schema_copies.py`, and the `$id` of `packages/maxitor/tools/graph_builder/maxitor/graph_builder/config_schema.json` to the file's new raw address
- [x] T017 [US1] Run `uv sync --all-extras`, then `bash scripts/check_before_commit.sh` until green, and `cmp` both graph files against the baseline
- [x] T018 [US1] Confirm `find packages/maxitor -type d -name src -not -path '*/node_modules/*'` shows only `packages/maxitor/front/client/src`, and that `graph-builder` and `repo-graph-port` start after a clean install of the built wheel

**Checkpoint**: show the diff and wait for the commit instruction.

---

## Phase 3: Rename `front` to `web` (commit 3)

**Goal**: folder, import path and extra all say `web`; the graph differs only by that name.

**Independent test**: the `sed | cmp` line of quickstart gives no output; `check_before_commit.sh` green.

**Rule (research R6)**: change identifiers only. Comments and docstrings that say "the front" in plain words stay, so the graph proof holds. The message in `launch.py` is the one text that changes.

- [ ] T019 [US3] `git mv packages/maxitor/front packages/maxitor/web` and `git mv packages/maxitor/web/maxitor/front packages/maxitor/web/maxitor/web`, and rewrite line 1 of every moved module
- [ ] T020 [US3] Replace `maxitor.front` with `maxitor.web` in every Python file, notebook and script outside `specs/`, past changelog entries and the graph files, including `packages/maxitor/web/`, `examples/`, `docs/reports/evidence/`, `docs/tutorials/step-26-maxitor.md` and `packages/maxitor/web/client/scripts/check-layout-determinism.ts`
- [ ] T021 [US3] Update `packages/maxitor/pyproject.toml`: extra `front` to `web`, `all` to `maxitor[web]`, the `maxitor` script to `maxitor.web.launch:main`, and every path. Run `uv lock` to update `uv.lock`
- [ ] T022 [US3] Update the message in `packages/maxitor/web/maxitor/web/launch.py`: `FRONT_HINT` to `WEB_HINT`, with the text `maxitor needs its web part: pip install "maxitor[web]"`, and the expected text in `packages/maxitor/web/tests/test_launch.py` and `tests/packaging/test_wheel_install_smoke.py`
- [ ] T023 [P] [US3] Update `pyproject.toml` and `scripts/package_boundaries.toml` paths to `packages/maxitor/web` and `packages/maxitor/web/maxitor`, and `AOA_ONLY_IN_EXTRA` in `scripts/check_package_metadata.py` to `web`
- [ ] T024 [P] [US3] Update `scripts/check_run.py` (`CLIENT`, the test package `maxitor/web`) and the client's folder in `scripts/run_checks_with_log.sh`
- [ ] T025 [P] [US3] Update `graph-builder.toml` (the build module `maxitor.web.build_graph`, the file `packages/maxitor/web/graph.json`)
- [ ] T026 [P] [US3] Update `.github/workflows/ci.yml`, `.github/workflows/publish.yml`, `deploy/stand/docker-compose.yml`, `.gitignore`, `.claude/launch.json`, `.vscode/launch.json` and `packages/maxitor/web/Dockerfile`, including its `--extra web`
- [ ] T027 [US3] Run `uv sync --all-extras`, then `uv run --extra dev ruff check --fix packages/ tests/ scripts/`, and review the reordered imports (research R7)
- [ ] T028 [US3] Run `uv run --extra dev graph-builder write`, then the `sed | cmp` line of quickstart, and `cmp` for `packages/maxitor/tools/repo_graph_port/graph.json`. Adversarial: change one id in `packages/maxitor/web/graph.json`, confirm `cmp` reports it, and regenerate
- [ ] T029 [US3] Run the old-names search and the `find` of quickstart, leaving aside the prose rule of research R6, then `bash scripts/check_before_commit.sh` until green
- [ ] T030 [US2] Build both images: `packages/maxitor/web/Dockerfile` and `packages/maxitor/tools/repo_graph_port/Dockerfile`. Then repeat the wheel check for `maxitor/web/static/`

**Checkpoint**: show the diff and wait for the commit instruction.

---

## Phase 4: Closing (commit 4)

**Goal**: the three tail steps of Principle VI, in this order and no other.

**Independent test**: the check run is at zero, every path in the docs exists, one changelog article is in place.

- [ ] T031 [US4] The check run, taken to zero: `bash scripts/run_checks_with_log.sh` with every remark fixed, the two accepted remarks aside
- [ ] T032 [US4] The documentation: every README tree and every path in `packages/maxitor/README.md`, `packages/maxitor/web/README.md`, the READMEs of the tools and core parts, `docs/tutorials/step-26-maxitor.md` and `examples/` show the new layout and `maxitor[web]`. The note that each checkout needs `uv sync` after the merge goes into the repository's contributor docs where setup is described. Run `examples/step_26_maxitor/13_maxitor_parts.py` and `05_full_graph_in_the_browser.py`, and update the matching notebooks with what they actually print
- [ ] T033 [US4] The changelog: one article in `docs/CHANGELOG.md`, in plain words, about what changed for a user: the extra is now `maxitor[web]`, and nothing else in an install changes

**Checkpoint**: show the diff and wait for the commit instruction. After the commit and the push, on instruction, `bash scripts/check_before_pr.sh` runs on the pushed commit before any pull request.

---

## Dependencies

- The order is strict: Phase 1 → 2 → 3 → 4. Phase 3 assumes the flat shape, and the closing phase assumes the code is settled.
- US1 and US2 share phases 1 and 2. US2 is finished by T030, when the image and wheel checks pass under the new name.
- Tasks marked [P] touch different files and can go in any order inside their phase. Each phase's verification tasks come after them.

## Implementation strategy

There is no useful partial stop for a user, but each phase is a safe stopping point for the repository: the check run is green on each commit. The moves (phases 1–2) carry the risk, and the graph comparison proves them neutral before the rename touches anything.
