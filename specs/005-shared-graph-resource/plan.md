# Implementation Plan: One shared coordinator graph, declared once

**Branch**: `feature/issue-213-shared-graph-resource` | **Date**: 2026-10-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-shared-graph-resource/spec.md`

## Summary

Maxitor's six diagram routes declare their graph connection as `PerCallConnection(factory=lambda: fastapi_app.state.duckdb_graph)` — a declaration that says "a fresh resource for every call" while the factory hands back one application-scoped slot. The feature replaces that value with **one ready resource, built once while the application is built**: a small `BaseResource` that holds the application and resolves the currently loaded graph on every read. The framework needs nothing: a ready `BaseResource` is already a legal value in `connections`, and `ConnectionValidator` checks only `isinstance(value, BaseResource)` against the actions' `@connection(DuckDBGraphResource, key=…)` declaration, so the declared type is metadata and the supplied value may be the holder. The failure raised while serving that request changes from `TypeError: PerCallConnection factory for key 'DuckDBGraph' must return BaseResource, got 'NoneType'` to a `HandleError` naming the situation — and nothing else changes, by the maintainer's decision: no handler, no status, no body. That decision costs nothing, because the adapter's `_CatchAllErrorsMiddleware` already answers every uncaught exception with one generic `500` and **logs nothing** (measured — [research.md](./research.md) R8), so the clearer message is read only where the resource is driven directly. One module is added, one edited, and two test modules appear; `packages/aoa-action-machine/` is untouched.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12"` in `packages/aoa-maxitor/pyproject.toml`; PEP 695 generics and `type` aliases are already used across the workspace)

**Primary Dependencies**: `aoa-action-machine`'s resource subsystem — `BaseResource`, the `@meta` decorator, `HandleError` — and FastAPI, already a dependency through `aoa-fastapi-adapter`; `duckdb` for the graph the holder delegates to; `httpx` and `fastapi.testclient` for the new test. **No new dependency is introduced.**

**Storage**: none added. The loaded graph already lives in `app.state.duckdb_graph` as an in-memory DuckDB snapshot; the feature changes who reads that slot and how the read is declared, not what is stored

**Testing**: pytest with `pytest-asyncio` (`asyncio_mode = "auto"`, `pythonpath = ["src"]`, `testpaths = ["tests"]` in `packages/aoa-maxitor/pyproject.toml`), run per package and again by the repository check run. The feature adds the **first test in this repository that builds the Maxitor app** (`create_app()` + `fastapi.testclient.TestClient`); every existing Maxitor test exercises an action or a resource directly, with no ASGI app

**Target Platform**: the Maxitor ASGI application (`aoa.maxitor.api.app`) as served by uvicorn and hosted through nginx at `/maxitor/`, plus the repository-wide check run (`bash scripts/run_checks_with_log.sh`)

**Project Type**: a consumer change inside the monorepo — `packages/aoa-maxitor` only. One new module, one edited module, one new test module, one changelog entry. No library, CLI or wire-format change; no change under `packages/aoa-action-machine/`

**Performance Goals**: none. The change adds one attribute lookup per read and removes one lambda call per request; no I/O, no per-request object allocation, and no measurable target is introduced

**Constraints**: FR-013 forbids any file under `packages/aoa-action-machine/` from changing, so the work must not "fix" the framework even opportunistically; the actions' `@connection` declarations and the connection key `DuckDBGraph` stay exactly as they are, because Maxitor's published graph metadata is read from them; the six routes' JSON must stay byte-identical for any loaded graph; the HTTP answer for an unloaded viewer must stay what it is today (Clarifications); the new module carries the line-1 path comment, the `═══` 79-column section rule, a one-line title, `PURPOSE` and `ARCHITECTURE / DATA FLOW` sections, an AI-CORE block with `ROLE`/`CONTRACT`/`INVARIANTS`, and one-line docstrings on class and methods; the holder must be bound to the application object rather than to a module global, because the test suite builds more than one app in a process

**Scale/Scope**: 1 new source module (~55 lines), 1 edited source module (9 lines: one import out, one import in, one construction, six connection values), 2 new test modules (the resource's contract and the routes' contract, ~12 tests), 1 runnable example script plus its notebook, 1 changelog article, the check run. Zero files under `packages/aoa-action-machine/`, zero `@connection` edits, zero client/TypeScript changes, zero schema changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, pull request or merge is part of executing this plan without an explicit instruction in the current turn | PASS — the plan produces files only; the branch already exists on the maintainer's instruction |
| II. English in commits, in git and in code | Every new file — module header, docstrings, comments, tests, the changelog article and the commit message — in English | PASS — planned |
| III. Module headers | The new module opens with `# packages/aoa-maxitor/src/aoa/maxitor/api/duckdb_graph_holder.py`, a `Name — purpose.` first line, and the 79-column `═` sections, `PURPOSE` and `ARCHITECTURE / DATA FLOW` among them | PASS — planned; `app.py` already complies and gains no header change |
| IV. AI-CORE blocks | `DuckDBGraphHolder` is a public class and carries `ROLE`, `CONTRACT` and `INVARIANTS`; no block in a module docstring, none on a method | PASS — planned |
| V. Short docstrings | Every new class and method gets its one-line docstring ending with a period, identifiers in double backticks | PASS — planned |
| VI. Check run, documentation, changelog | Exactly three closing tasks, in that order, and no other task absorbs them | PASS — T014–T016. The documentation task carries both what this change owns: the new module's header, AI-CORE block and docstrings, **and** the runnable example plus notebook that points 4–6 require for the cases the change introduces. No `docs/` page is written, because the only page that states the removed shape is the tutorial the maintainer ruled out of scope |
| Final step: the check run | `bash scripts/run_checks_with_log.sh` is the last step, and every remark it reports is fixed | PASS — closing task, taken to zero; the two accepted remarks (Vite chunk size, LangGraph deprecation) are the only ones allowed to stand |

**One place where the plan reads the constitution against the repository's practice**, recorded rather than silently resolved: Principle VI says the changelog article goes to `docs/CHANGELOG.md`, but this repository now keeps a per-package changelog and updated `packages/aoa-maxitor/CHANGELOG.md` for the last Maxitor-facing change (#199), while `docs/CHANGELOG.md` was last written for a framework-level change (#196). The closing changelog task writes **one** article in the package changelog under `[Unreleased]`, and adds the `docs/CHANGELOG.md` line only if the maintainer judges this work framework-level. That is a question for the maintainer at that task, not a licence to write two articles.

**A second tension inside the constitution itself**, recorded for the same reason. Principle VI fixes the tail as check run → documentation → changelog, while the section *Final step: the check run* says the check run "is the last step of any change". The tasks follow Principle VI's explicit ordering, because it is the more specific instruction and the one that reserves three named tasks. The ordering is also coherent: the two steps after the run write prose and a runnable example, neither of which the run measures — `ruff`, mypy, pylint, the packaging checks and the test suite all inspect code, and neither a Markdown article nor an executed example script changes the code they read. The example script is the one artefact worth a second thought, and it is executed with the repository's own environment while it is written (Principle VI, point 6), so a broken example is caught where it is written rather than by the check run. If the maintainer reads the two sections the other way, the tail becomes documentation → changelog → check run, and T014–T016 are reordered — nothing else in this plan changes.

**Re-check after Phase 1 design**: no new dependency, no new package, no new public surface outside `aoa.maxitor.api`, no file under `packages/aoa-action-machine/`, and no change to the six routes' contract. Every gate above still passes, and **Complexity Tracking** stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/005-shared-graph-resource/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # The capability, clarified (2 questions, 2 answers)
├── research.md          # Phase 0 output: the decisions behind the design
├── data-model.md        # Phase 1 output: the slot, the holder, and the states of a read
├── quickstart.md        # Phase 1 output: how to prove it works
├── checklists/
│   └── requirements.md  # Spec quality checklist (16/16 passing)
├── contracts/           # Phase 1 output: the two surfaces this change fixes
│   ├── resource.md          # What the holder is and must expose
│   └── routes.md            # What the six routes answer, before and after a load
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/aoa-maxitor/
├── src/aoa/maxitor/api/
│   ├── app.py                       # EDIT: six connection values become one ready resource;
│   │                                #       the per-call import goes, the holder import arrives
│   └── duckdb_graph_holder.py       # NEW: the app-scoped holder — mode 1 over the loaded graph
├── tests/
│   ├── test_api_duckdb_graph_holder.py  # NEW: the resource's contract — one instance per app,
│   │                                    #      resolve-per-read, the two operations, no lifecycle
│   └── test_api_diagram_routes.py       # NEW: the routes' contract — the six share one holder,
│                                        #      the baseline unchanged, the reload, the failed load
└── CHANGELOG.md                     # EDIT: one article under [Unreleased] (the closing task)

examples/step_26_maxitor/
├── 02_api_shared_graph.py           # NEW: the runnable case — before a load, after a load, a reload
└── 02_api_shared_graph.ipynb        # NEW: the same case, cell by cell (Principle VI, points 5–6)
```

Unchanged, and asserted to be unchanged: `packages/aoa-action-machine/**` (every file), the six actions' `@connection` declarations in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/`, `packages/aoa-maxitor/src/aoa/maxitor/api/routes/load.py` and `…/sidebar.py`, and every file under `packages/aoa-maxitor/client/`.

**Structure Decision**: the holder lives in `aoa/maxitor/api/` directly beside `app.py`, not in `model/diagrams/resources/`. It reads FastAPI application state, so it is an API-layer object; the resources folder holds graph-domain resources whose subject is the coordinator model, and a holder that exists only because an ASGI application has a slot does not belong among them. The issue proposed the same location (`api/duckdb_graph_holder.py`) and the maintainer carried that decision into the spec.

The holder subclasses **`BaseResource` directly**, not `ExternalServiceResource`. `ExternalServiceResource.__init__` stores a service instance, and the holder has none at construction time — the graph does not exist yet. Subclassing it would force a placeholder service and a mutation on every read, which is the very "one object that pretends to be another" the feature removes. Subclassing `BaseResource` costs three small members and states the truth: this is one application-scoped resource whose value is read late.

Delegation is **explicit**, never `__getattr__`: the two members the six actions actually use are `service` and `execute_fetch_dicts` (measured — `list_node_types_action.py:163`, `list_domains_action.py:138`, `list_entities_action.py:301-331`, `full_graph_action.py:143`, `get_lifecycle_finite_automaton_action.py:124-191`, `domain_use_case_diagram_action.py:42-267`, and `left_sidebar_action.py:202-244` on the load path). Attribute forwarding would also be a silent contract widening, which is why the repository bans `__getattr__` in package `__init__.py` files.

The two test modules sit in `packages/aoa-maxitor/tests/` with the others and follow the naming already in use. They are the first app-level tests in the repository, which is a deliberate cost: the acceptance for this feature is partly about **declarations on routes**, and a test that never builds an app cannot observe a declaration on a route. They are split by subject — the resource's contract in one, the routes' contract in the other — because they need different instruments (one drives the resource, the other drives the application) and because tasks that extend one file can never be honestly marked parallel.

**One claim this plan had to prove differently than expected.** "One object, declared once" cannot be checked by reading the route registrations back: `FastApiAdapter.build()` closes each endpoint over its record, and `create_app()` discards the adapter that holds them, so nothing exposes the declared value once the app is built. The claim is therefore proved by counting real `DuckDBGraphHolder` constructions during the real `create_app()` (exactly one per application) together with the routes all reading the one slot. [research.md](./research.md) R10 records the measurement, the chosen instrument and why reaching into the endpoints' closures was rejected.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations — the table is intentionally empty. The one place where the plan reads the constitution against repository practice is recorded in the Constitution Check above and costs one question at the changelog task, not a violation.
