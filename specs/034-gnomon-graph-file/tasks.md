# Tasks: A Service Keeps Its Current Graph in One File, by the Format of maxitor-gnomon

**Input**: Design documents from `specs/034-gnomon-graph-file/`

**Prerequisites**: plan.md, spec.md (US1–US7), research.md (R1–R10), data-model.md, contracts/gnomon.md, quickstart.md

**Tests**: Required. Every new test is verified adversarially: break the code the way the test must catch, confirm that test fails and no other does, restore.

**Organization**: one phase = one commit. Commit 1 holds the design documents; commits 2–7 are #301's phases 1–6; #301's phase 7 is three commits (check run, documentation, changelog), commits 8–10.

**Issue checkboxes**: #301 "Phases" has seven. Commit 2 → phase 1; 3 → 2; 4 → 3; 5 → 4; 6 → 5; 7 → 6; commits 8–10 → phase 7 (ticked after commit 10). Every tick carries its sha (`gh issue edit 301`, the body fetched and checked for length before it is written back).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story of spec.md (US1–US7)
- Every new Python module opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` (constitution III); every public type and function of contracts/gnomon.md carries an AI-CORE block (IV); every class, function and method a one-line docstring (V).
- `G` below is `packages/maxitor-gnomon`; `GS` is `packages/maxitor-gnomon/src/maxitor_gnomon`.

---

## Phase 1: Setup — design documents (commit 1)

- [x] T001 Prepare commit 1 with `specs/034-gnomon-graph-file/` only (spec, plan, research, data model, contract, quickstart, `checklists/requirements.md`, tasks; `tasks.ru_draft.md` stays out): `docs(spec): specify the graph file and maxitor-gnomon (#301)`. `.claude/launch.json` stays out.

---

## Phase 2: The package (commit 2) · US4 — #301 phase 1

**Goal**: an empty, published-like package that cannot import AOA (FR-001, FR-011).

- [x] T002 Baseline: on `feature/issue-301-gnomon-graph-file` (off `feature/issue-273-graph-history` at `9fe5d843`) run `bash scripts/run_checks_with_log.sh`; record the wall time and the 37 `OK` here. **Done:** 37 `OK`, no `FAIL`, wall time 62.0 s.
- [x] T003 [US4] Create `G/pyproject.toml` (name `maxitor-gnomon`, version `0.1.0`, `requires-python = ">=3.12"`, license as the other packages, no dependencies yet — `jsonschema` arrives with the schemas in T010 and the console script `gnomon = "maxitor_gnomon.cli:main"` with `cli.py` in T021, so no commit ships a dependency it does not use or a command that cannot start, wheel `packages = ["src/maxitor_gnomon"]`, `testpaths = ["tests"]`), `G/LICENSE` and `G/NOTICE` copied from `packages/aoa-otel`, `G/CHANGELOG.md`, a placeholder `G/README.md`, `GS/__init__.py` (module header, `__version__`), `GS/py.typed`, and `G/tests/test_package.py` (the package imports and states its version).
- [x] T004 [US4] Add `packages/maxitor-gnomon` to `[tool.uv.workspace].members` and `maxitor-gnomon = { workspace = true }` to `[tool.uv.sources]` in the root `pyproject.toml`; add `packages/maxitor-gnomon/src` to the mypy `files` list and `mypy_path`, and `packages/maxitor-gnomon/src/maxitor_gnomon` to `[tool.vulture].paths`; run `uv sync`. **Done:** also in the root `dev` extra (so the root environment has it for its pytest step), the pytest `pythonpath` and `task build-packages`.
- [x] T005 [US4] The boundary rule (research R2): in `scripts/package_boundaries.toml` add `[standalone.gnomon] roots = ["packages/maxitor-gnomon/src/maxitor_gnomon"]`; in `scripts/check_package_boundaries.py` read `[standalone.*]` and fail on any `import aoa…` / `from aoa…` under those roots, naming file and line. **Done:** the table sits at the end of the file — a key written after a `[table]` header belongs to that table. (Found on the way and left alone: the existing top-level `allow = []` follows `[packages.examples]`, so TOML reads it as `packages.examples.allow` and the checker never sees an allow list; it is empty, so nothing is lost today.) `scripts/check_package_metadata.py` also lists `maxitor-gnomon`, with every `aoa-*` distribution forbidden as its dependency.
- [x] T006 [US4] The packaging smoke test: in `tests/packaging/test_wheel_install_smoke.py` let a distribution declare its own top-level prefix (`maxitor-gnomon` → `maxitor_gnomon/`) and require that its wheel ships nothing under `aoa/`; add `maxitor-gnomon` to the build loop of `scripts/check_run.py` (`PACKAGES`) and a `Pytest maxitor-gnomon` step; add a `publish-maxitor-gnomon` job and the `maxitor-gnomon` option to `.github/workflows/publish.yml`, as for the other packages. **Done:** the smoke test maps each distribution to its own tree (`_DIST_TREE`), forbids every other tree and, outside the `aoa` namespace, anything under `aoa/`; a new test installs the gnomon wheel alone in a clean environment and finds no `aoa`. `publish.yml` also takes the tag `maxitor-gnomon-v*`.
- [x] T007 [US4] Adversarial check: add `import aoa.action_machine` to `GS/__init__.py` → only `Package import boundaries (production)` fails; put a file under `aoa/` into the wheel's sources → only the smoke test fails. Restore. Record here. **Done, full check run each time:** (1) a used `import aoa.action_machine` in `__init__.py` → `FAIL Package import boundaries (production)` (`__init__.py:28: context 'gnomon' must not import package 'aoa' via 'aoa.action_machine'`) and `FAIL Packaging wheel install smoke` (`test_clean_install_gnomon_brings_no_aoa`: the wheel cannot import in a clean environment) — two guards, one static and one installed, nothing else failed; (2) `force-include` of `aoa/stray.typed` into the wheel → only `FAIL Packaging wheel install smoke` (`forbidden prefix 'aoa/': ['aoa/stray.typed']`, and the clean install finds `aoa`). Both restored byte for byte.
- [x] T008 [US4] Check run green (39 steps: two new) — **39 `OK`, 63.8 s**; prepare commit 2: `feat(gnomon): add the maxitor-gnomon package (#301)`; tick #301 phase 1.

---

## Phase 3: The graph schema, by version (commit 3) · US4 — #301 phase 2

**Goal**: the schema lives in the package, by version; AOA reads it from there (FR-002 – FR-004).

- [x] T009 [US4] `GS/schemas/graph/1.1.json` = `git show HEAD:packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.json` byte for byte except `$id`; `GS/schemas/graph/1.0.json` = the same file at `f260e2e6`, with its own `$id`. Each `$id` names its version (`https://github.com/bystrovmaxim/aoa/…/schemas/graph/1.1.json`). **Done:** `1.1.json` is AOA's file byte for byte apart from `$id` and the title, which the maintainer renamed in both versions to `Gnomon node graph JSON schema` before anything was published; `1.0` and `1.1` differ only in the edge's required `id` and the version's `const`.
- [x] T010 [US4] Add the dependency `jsonschema>=4.17,<5` to `G/pyproject.toml`. `GS/schemas.py`: `SCHEMA_VERSIONS = ("1.0", "1.1")`, `graph_schema(version) -> dict` (read with `importlib.resources`, cached), `GraphRefused(ValueError)` with `version`, `path`, `reason`, and `check_graph(document) -> None` — a missing `schema_version` or an unknown one is refused by name; otherwise the first JSON Schema error with its JSON path. **Done:** as the package `GS/schemas/__init__.py` with the files under `GS/schemas/graph/` — a module `schemas.py` beside a folder `schemas/` would shadow it. A union (`oneOf`) refusal is narrowed to the one branch whose `const`/`enum` matched, so a bad edge says `edges/3: 'id' is a required property` or `edges/3/source_id: 5 is not of type 'string'`; when no branch was meant, `edges/3: matches none of the shapes allowed here` instead of the whole value. `GraphRefused` keeps its name: `N818` is ignored for the package in the root `pyproject.toml`, with the reason, as for AOA's access answers.
- [x] T011 [US4] AOA: in `packages/aoa-action-machine/pyproject.toml` add the dependency `maxitor-gnomon` (and `[tool.uv.sources]` workspace entry); `graph_json_schema.py` sets `GRAPH_JSON_SCHEMA = graph_schema("1.1")` and its header says where the schema lives now; delete `graph_json_schema.json`; the package boundary for `action_machine` allows importing `maxitor_gnomon` (it is not an `aoa` package, so check that the checker does not flag it). **Done:** the boundary checker does not flag `maxitor_gnomon` in AOA. The packaging smoke test installs the gnomon wheel beside `aoa-action-machine` and loads `GRAPH_JSON_SCHEMA` in the clean environment.
- [x] T012 [P] [US4] Tests in `G/tests/test_schemas.py`: the demo's 1.1 export passes; the same without one edge's `id` is refused naming `edges/…/id`; gameoffer's snapshot 006 (a fixture `G/tests/fixtures/graph-1.0.json`, cut to a small valid sample) passes against 1.0; `"9.9"` is refused naming `9.9`; no `schema_version` is refused; `graph_schema("1.1")` equals AOA's `GRAPH_JSON_SCHEMA`, and its content apart from `$id` has the SHA-256 that the schema file had before this phase (recorded in the test, taken in T009). **Done:** 14 tests. The samples are cut from the demo's graph, one edge of each of its 28 types and their 38 nodes (`G/tests/fixtures/graph-1.1.json`, and `graph-1.0.json` without the edge ids) — gameoffer is private and this repository public, so none of its data is copied here; instead all 13 of its `graph_history` snapshots (two services, 296/370 to 517/646 nodes/edges) were checked once against 1.0 on this machine: all pass. The hashes cover both published versions. AOA's side is `packages/aoa-action-machine/tests/action_machine/graph/test_graph_json_schema_source.py`.
- [x] T013 [US4] Run every suite: `aoa-action-machine`, `aoa-maxitor`, `aoa-demo` pass unchanged (SC-005). Adversarial check: change one character of `1.1.json` → the hash test and the AOA schema tests fail, nothing else; remove `"1.0"` from `SCHEMA_VERSIONS` → only the 1.0 test fails. Restore. Record here. **Done, full check run each time:** one character of `1.1.json`'s title → only `Pytest maxitor-gnomon` fails, `test_a_published_version_never_changes[1.1]` (the AOA tests do not see a title, so the hash is the guard); `SCHEMA_VERSIONS = ("1.1",)` → only `Pytest maxitor-gnomon` fails (`test_an_unknown_version_is_refused_by_name`, `test_a_published_version_never_changes[1.1]`). Restored. The first run of the first break also found two real faults of this phase, since fixed: Ruff (`N818`, an unescaped `match=`) and the clean install of `aoa-action-machine` without the gnomon wheel. `aoa-action-machine`'s 385 graph tests pass unchanged.
- [x] T014 [US4] Check run green — **39 `OK`, 63.9 s**; prepare commit 3: `feat(gnomon): the graph schema by version, read by AOA (#301)`; tick #301 phase 2.

---

## Phase 4: The config (commit 4) · US5 — #301 phase 3

- [x] T015 [US5] `GS/schemas/config/1.0.json` and `GS/config.py`: `Graph` (frozen: `name`, `cwd: Path`, `build: str`, `file: Path`), `ConfigRefused(ValueError)` with `graph`, `field`, `reason`, and `read_config(path) -> list[Graph]` — `gnomon = "1.0"` required; each `[[graph]]` needs `name`, `build`, `file` ("required"), `cwd` defaults to `"."`; names unique; files unique; paths resolved against the config's folder; graphs in file order. **Done:** the config's own version is checked before its schema, so `gnomon = "2.0"` is named rather than reported as a schema error; an unknown field is refused too (`graph 'demo', bild: not a field of the config`); a missing file is a refusal (`no config at …`). A refusal reads as one line: `graph 'demo', file: required`.
- [x] T016 [P] [US5] Tests in `G/tests/test_config.py`: a valid config gives its graphs in order with resolved paths; each refusal — missing `name`, missing `build`, missing `file`, a repeated name, two graphs with one file, no `gnomon` key, an unknown `gnomon` version, not TOML — names the graph and the field. **Done:** 17 tests (31 in the package): the two orders and path rules, seven graph refusals (no name, no build, no file, an unknown field, a name that is not text, a repeated name, one file twice), `./packages/../graph.json` and `graph.json` seen as one file, five config refusals (no version, `2.0`, no graphs, an empty list, not TOML), a missing config, the one-line message.
- [x] T017 [US5] Adversarial check: drop the unique-file rule → only its test fails; default `cwd` to the current folder instead of the config's → only the path test fails. Restore. Record here. **Done, full check run each time, on code mypy already accepted:** the unique-file rule removed → only `Pytest maxitor-gnomon` fails (`one-file-twice`, `test_two_paths_to_one_file_are_one_file`); `cwd` from the current folder → only `Pytest maxitor-gnomon` fails (`test_a_valid_config_gives_its_graphs_in_order`, `test_paths_are_relative_to_the_config_not_to_the_caller`). Restored. The first runs of both breaks had also shown a real fault of this phase, since fixed: mypy on `ValidationError`'s loosely typed fields, narrowed with `isinstance`.
- [x] T018 [US5] Check run green — **39 `OK`, 64.7 s**; prepare commit 4: `feat(gnomon): read gnomon.toml (#301)`; tick #301 phase 3.

---

## Phase 5: `gnomon write`, `check`, `validate`, `skill` (commit 5) · US2, US3 — #301 phase 4

- [ ] T019 [US2] `GS/differences.py`: `differences(old, new, limit=20) -> list[str]` per research R6 — top level by key; arrays of objects that all carry `id` by `id` (added / removed / changed, recursing into changed); objects by key; other values by equality; lines like `edges[id=…].target_id: A → B`, `nodes[id=…]: added`, `schema_version: 1.0 → 1.1`; `… and N more` past the limit.
- [ ] T020 [US2] `GS/writer.py`: `render(document) -> bytes` (`json.dumps(…, ensure_ascii=False, sort_keys=True, indent=2) + "\n"`, UTF-8); `build(graph) -> dict` (run `graph.build` with `bash -c` in `graph.cwd` as its own process, timeout 300 s, capture stdout and stderr; a non-zero exit, a timeout, output that is not JSON → `BuildFailed` with the command and the output's tail; then `check_graph`); `write(graphs) -> list[Outcome]` (writes a file only if its bytes differ); `check(graphs) -> list[Outcome]` (writes nothing; stale → `differences`, or "only the formatting differs"; missing file).
- [ ] T021 [US2] Add the console script `gnomon = "maxitor_gnomon.cli:main"` to `G/pyproject.toml`. `GS/cli.py`: `gnomon write [--config]`, `gnomon check [--config]`, `gnomon validate <file | ->` (prints `ok <version>: <n> nodes, <m> edges` or the refusal), `gnomon skill` (prints the skill file; until phase 7 it does not exist yet, so phase 5 prints a clear "no skill shipped" and phase 7 replaces it); output and exit codes exactly as in contracts/gnomon.md (0 / 1 / 2); every failure ends with the fixing command `gnomon write --config <path>`.
- [ ] T022 [P] [US3] Tests in `G/tests/test_writer.py` with tiny configs whose `build` is `python -c "print(...)"`: two writes give the same bytes; a second write of an unchanged graph leaves the file's bytes and modification time as they were; `check` passes right after `write`; after the build prints a changed graph, `check` fails listing the differences by id; a re-indented file gives "only the formatting differs"; a missing file; a build that exits 3, one that prints `oops`, one that prints a 1.1 graph without an edge `id`, one that sleeps past a 1 s test timeout — each refused naming the graph, nothing written.
- [ ] T023 [P] [US2] Tests in `G/tests/test_differences.py` and `G/tests/test_cli.py`: added, removed and changed by id, nested property paths, the limit, formatting-only; the CLI's exit codes 0 / 1 / 2 and `validate` from a file and from standard input.
- [ ] T024 [US2] Adversarial check, one at a time: sort keys off → the same-bytes test fails; always rewrite the file → only the modification-time test fails; compare arrays by position instead of `id` → only the by-id test fails; drop `check_graph` before writing → only the invalid-graph test fails. Restore. Record here.
- [ ] T025 [US2] Check run green; prepare commit 5: `feat(gnomon): gnomon write, check and validate (#301)`; tick #301 phase 4.

---

## Phase 6: The demo's and Maxitor's graph files (commit 6) · US6 — #301 phase 5

- [ ] T026 [P] [US6] `packages/aoa-demo/src/aoa/demo/graph_json.py`: imports the demo's sample modules (`import_sample_registration_modules()`) and prints `build_registered_interchange_coordinator().to_json()` when run as `python -m aoa.demo.graph_json`; nothing else is printed.
- [ ] T027 [P] [US6] `packages/aoa-maxitor/src/aoa/maxitor/graph_json.py`: imports `aoa.maxitor.api.app` (which loads Maxitor's actions) and prints `create_node_graph_coordinator().to_json()` when run as `python -m aoa.maxitor.graph_json`.
- [ ] T028 [US6] Root `gnomon.toml` (`gnomon = "1.0"`; `demo` → `uv run --extra dev python -m aoa.demo.graph_json`, file `packages/aoa-demo/graph.json`; `maxitor` → `uv run --extra dev python -m aoa.maxitor.graph_json`, file `packages/aoa-maxitor/graph.json`); run `uv run gnomon write`; exclude `graph.json` from both packages' sdists (`[tool.hatch.build.targets.sdist] exclude`).
- [ ] T029 [US6] `scripts/check_run.py`: a `Step` field `only_if_all_passed`; the step `Graph files (gnomon write)` (`uv run gnomon write`) starts after every other step has ended and only if all passed; otherwise its block reads `SKIPPED Graph files (gnomon write): N step(s) failed` and counts neither as `OK` nor `FAIL`; the header comment says so.
- [ ] T030 [US6] Verify per quickstart §1, §2, §4, §7: two writes, `git status` clean; a changed demo field → `gnomon check` names it by id; `3213 4841` and `0 0`; a green run ends with `OK Graph files`, a run with one failing step ends with `SKIPPED`. Adversarial: build the demo and Maxitor in one process (a single command importing both) → the `0 0` check fails; make the step run despite a failure → the skip test fails. Restore. Record the step's time in a green run here (SC-006).
- [ ] T031 [US6] Prepare commit 6 with `gnomon.toml`, both `graph.json`, both modules, the sdist excludes and `check_run.py`: `feat(graph): the demo and Maxitor save their graphs (#301)`; tick #301 phase 5.

---

## Phase 7: The `gnomon-setup` skill (commit 7) · US7 — #301 phase 6

- [ ] T032 [US7] `GS/skills/gnomon-setup/SKILL.md` per research R10, one self-contained file: front matter (`name: gnomon-setup`, a description for "set up or check a project's graph history"); "If you read this from a link" (save into `.claude/skills/gnomon-setup/`, `.cursor/skills/gnomon-setup/` or `.dsh/skills/gnomon-setup/`, then go on at once); how to run `gnomon` (from git before publication, a pinned commit in CI, from PyPI after); **Setup** as numbered steps — read `gnomon.toml`; check every configured graph (build, `gnomon validate -`, `gnomon check`); search for every other place producing a graph document; draft and prove a build command for each in its own process; for each graph propose where its file goes (the repository's own conventions first, then `<service folder>/graph.json`, or the user's choice); one table (service, folder, command, proof, file and alternatives, state: current / stale / broken / new / refused); ask; then edit `gnomon.toml`, `gnomon write`, add `gnomon check` to the CI the project uses (asking which), `gnomon check`; never commit. An example `gnomon.toml` and a GitHub Actions step inside the file. `gnomon skill` now prints it; the wheel ships it (smoke test).
- [ ] T033 [US7] Check the skill on this repository, each in a fresh agent session, recording what it showed and asked: with `gnomon.toml` moved away → it finds the demo's and Maxitor's graphs, proves them and asks where to save, offering the existing `packages/*/graph.json`; with it back → it reports both current; with `maxitor`'s `build` broken → it reports that entry broken. Fix the skill until all three go as written.
- [ ] T034 [US7] Prepare commit 7: `feat(gnomon): the gnomon-setup skill (#301)`; tick #301 phase 6.

---

## Phase 8: The check run (commit 8) · #301 phase 7

- [ ] T035 Run `bash scripts/run_checks_with_log.sh` and take it to zero — only the two accepted remarks stay; prepare commit 8: `chore: take the check run to zero (#301)`. If the first run is clean there is nothing to commit; record that here.

---

## Phase 9: Documentation (commit 9) · US1 — #301 phase 7

- [ ] T036 [US1] `G/README.md` per research R9: what the package is and its name; the graph document and matching by `id`; schema versions and the never-changed rule; `gnomon.toml` field by field; the four commands with real output; "How a graph travels with a pull request" (FR-012a, five steps); **three ways to start** (FR-012f) — by hand (Get started, numbered, with a GitHub Actions step and gameoffer's two services as the worked example), from the command line (`gnomon skill`), with a one-sentence prompt and the skill's raw link (`raw.githubusercontent.com/…/SKILL.md`). The Russian draft beside it (`G/README.ru_draft.md`).
- [ ] T037 [P] [US1] AOA's guide: `docs/tutorials/step-00-get-started.md` — "Save your graph from day one" after Installation option A (why, the three ways, the link), `maxitor-gnomon/` in the repository tree marked as independent of AOA, and the stale "three packages" wording fixed; `docs/tutorials/step-26-maxitor.md` — "The graph saved with every change" after "Every edge has an id" (the repository's two graph files and `gnomon.toml`, the PR flow, `gnomon check`'s real output); the root `README.md` packages table; a line under "VII Maxitor" in `docs/index.md`; one line on the graph step in `docs/how-to/run-the-checks.md`. Russian drafts beside the pages that have them.
- [ ] T038 [P] [US1] `examples/step_26_maxitor/12_graph_file.py` and its executed `12_graph_file.ipynb`, every case, writing only to a temporary folder: the repository's `gnomon.toml`; the demo's saved graph checked against its schema (version, counts); a rebuilt demo graph equal to its file; a stale copy with its differences by id; a re-indented copy — formatting only; a `9.9` document refused. Real output in the docstring; the notebook's output equals the script's.
- [ ] T039 [US1] Prepare commit 9: `docs(gnomon): save the graph with every change (#301)`.

---

## Phase 10: Changelog (commit 10) · #301 phase 7

- [ ] T040 One article at the top of `docs/CHANGELOG.md`: a service now keeps its graph in a file that changes with every merge, a new package `maxitor-gnomon` holds the graph's format and works for any project, and three ways to set a project up — plain words, no technical detail; its Russian version in `docs/CHANGELOG.ru_draft.md`. Prepare commit 10: `docs(changelog): <title> (#301)`; tick #301 phase 7.

---

## Dependencies & Execution Order

- Phases in order. Phase 3 needs the package (2); Phase 5 needs the schema (3) and the config (4); Phase 6 needs the commands (5); Phase 7 needs the commands (5) and is checked on Phase 6's files; the tail (8–10) comes last.
- T002 before any change.
- No commit, push, pull request or issue edit without the maintainer's word (constitution I).

## Parallel Opportunities

- T012 beside T011; T016 after T015; T022 and T023 beside each other; T026 and T027 beside each other; T037 and T038 beside each other.

## Implementation Strategy

- The result is the whole of Phases 2–7: the package, the schema, the config, the commands, the repository's two graphs and the skill — after it, any project can start saving its graph, and the maintainer tries the three ways to start on gameoffer (SC-001, SC-007).
- Then the tail closes #301. Publishing `maxitor-gnomon` to PyPI is a release step outside this plan.
