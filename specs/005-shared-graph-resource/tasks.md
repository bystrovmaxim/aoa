# Tasks: One shared coordinator graph, declared once

**Input**: Design documents from `specs/005-shared-graph-resource/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included. The specification's acceptance is stated as observable outcomes — the six routes share one graph object, the failure names the situation, the caller's response is unchanged — and none of it is visible without a test. This feature also adds the **first app-level tests in the repository** (`create_app()` + `TestClient`); every existing Maxitor test drives an action directly.

**Organization**: tasks are grouped by user story so each story is independently implementable and testable. The measured baseline comes first, because "unchanged" is a claim about a comparison. The holder is foundational, and it is deliberately built in two steps — first the delegation, then the refusal — so that User Story 2 has code of its own rather than being a test-only phase.

**Two test modules, not one.** The resource's own contract ([contracts/resource.md](./contracts/resource.md), C-1…C-4) and the routes' contract ([contracts/routes.md](./contracts/routes.md), R-1…R-4) are different subjects with different instruments: one drives the resource directly, the other drives the application. Splitting them keeps the `[P]` markers honest — tasks that share a file are never marked parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story the task serves (US1, US2)
- Every task names the exact file it touches

## Path Conventions

Repository root is the working directory. Every path in this feature is under `packages/aoa-maxitor/` — except the runnable example of T015 — and FR-013 forbids touching `packages/aoa-action-machine/` at all.

---

## Phase 1: Setup

**Purpose**: the comparison baseline. Every "unchanged" clause in the acceptance is measured against something, and that something has to be recorded before anything moves.

- [ ] T001 Record the before-state so "unchanged" is comparable, in `specs/005-shared-graph-resource/quickstart.md` § 0–1: run `uv run pytest packages/aoa-maxitor -q` and record the counts (measured today: **115 passed, 1 skipped**), then drive the current `create_app()` with `TestClient(app, raise_server_exceptions=False)` over all six diagram routes and record status and body per route (measured today: `500 {"detail":"Internal server error"}` for `/api/v1/list-domains`, `/api/v1/list-entities`, `/api/v1/list-node-types`, `/api/v1/full-graph`; `422` with a missing-parameter detail for `/api/v1/lifecycle-finite-automaton` and `/api/v1/domain-use-case-diagram`). Correct the quickstart's numbers in place if a fresh run disagrees — the recorded figures are evidence, not decoration.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the shared resource itself — the object both user stories are about. Built here without its refusal, which is User Story 2's own work.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

- [ ] T002 Create `packages/aoa-maxitor/src/aoa/maxitor/api/duckdb_graph_holder.py` holding `DuckDBGraphHolder`, per [contracts/resource.md](./contracts/resource.md) § 1–2 and [data-model.md](./data-model.md) E2. Subclass `aoa.action_machine.resources.base_resource.BaseResource` **directly** — not `ExternalServiceResource`, which requires a service at construction and there is none ([research.md](./research.md) R2). Carry the module header of Principle III: line 1 is `# packages/aoa-maxitor/src/aoa/maxitor/api/duckdb_graph_holder.py`, then a `Name — purpose.` first line and the 79-column `═` sections `PURPOSE` and `ARCHITECTURE / DATA FLOW`. Decorate with `@meta(description=…, domain=DiagramsDomain)` and give the class an AI-CORE block with `ROLE`, `CONTRACT` and `INVARIANTS` (Principle IV). Members, each with a one-line docstring ending in a period (Principle V): `__init__(self, app: FastAPI)` storing the application and resolving nothing; `get_wrapper_class()` returning `None`; `check_rollup_support()` returning `False`; a `service` property and `execute_fetch_dicts(self, sql, parameters=None)` that each call `self._resolve()` and delegate; and a private `_resolve()` that reads the slot with `getattr(self._app.state, "duckdb_graph", None)` and raises `HandleError("Graph is not loaded: call POST /api/load first.")` when it is `None` — **the refusal belongs to this task, not to US2**; see the note under T007. No `__getattr__` and no forwarding beyond those two members (C-2.3). Do **not** add `open`, `close`, `begin`, `commit` or `rollback` (C-4.1).

---

## Phase 3: User Story 1 — the diagram routes share one graph, and their declaration says so (Priority: P1) 🎯 MVP

**Goal**: the six registrations in `app.py` hand the routes **one ready resource** created while the application is built, in place of a `PerCallConnection` whose factory returned one application-scoped slot; all six read the same loaded graph, and their JSON is what it was.

**Independent Test**: build the app with a graph loaded, drive the six routes, and confirm each returns exactly the payload it returned before; then read the resource directly and confirm it is one instance per application, exposes only the two operations, and has no lifecycle (quickstart § 3, § 5).

- [ ] T003 [US1] Rewire `packages/aoa-maxitor/src/aoa/maxitor/api/app.py`: delete the `from aoa.action_machine.resources.per_call_connection import PerCallConnection` import (it is otherwise unused) and replace `duckdb_per_request = PerCallConnection(factory=lambda: fastapi_app.state.duckdb_graph)` with one `duckdb_graph = DuckDBGraphHolder(fastapi_app)`, built **after** `fastapi_app = FastAPI(...)` and **before** the first `.get(…)` registration, so the declaration is complete before any route exists (FR-002). Add `from aoa.maxitor.api.duckdb_graph_holder import DuckDBGraphHolder` in the sorted import block, before `from aoa.maxitor.api.routes.load import …`. Change all six `connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_per_request}` values to `duckdb_graph` — the six are `/list-domains`, `/list-entities`, `/list-node-types`, `/full-graph`, `/lifecycle-finite-automaton`, `/domain-use-case-diagram` (FR-001). Touch nothing else: the key, the actions, the routes' paths and the lifespan stay as they are (FR-010, FR-012)
- [ ] T004 [P] [US1] Write the **resource's** tests in `packages/aoa-maxitor/tests/test_api_duckdb_graph_holder.py`, per [contracts/resource.md](./contracts/resource.md) C-1…C-4. Cover, as separate named tests so `-k` selectors stay stable: (a) **one instance per application** — wrap `DuckDBGraphHolder` in the `aoa.maxitor.api.app` module namespace with a spy that records real constructions, call the real `create_app()`, and assert exactly one is built per call and that two applications get different instances. This is the only way to observe the declaration, because `create_app()` discards the adapter that holds the route records, so no registration is reachable afterwards ([research.md](./research.md) R10); (b) **resolve per read, cache nothing** — point `app.state.duckdb_graph` at a recording stand-in, read `service` and `execute_fetch_dicts` twice, confirm the same object both times, then replace the slot and confirm the next read returns the new one (SC-003, C-2.1); (c) **bound to its application** (SC-004, C-1.3); (d) **the surface is exactly two operations** — `service` and `execute_fetch_dicts` — and an attribute the loaded graph has but the routes do not use is not reachable through the holder (FR-006, SC-008, C-2.3); (e) **no lifecycle** — no `open`, `close`, `begin`, `commit` or `rollback`; `get_wrapper_class()` is `None`; `check_rollup_support()` is `False`; and a request driven through a route constructs no wrapper (FR-009, SC-009, C-4.1, C-4.2) — name this one with `lifecycle` in it, because [quickstart.md](./quickstart.md) § 5 selects it by that word. Do **not** publish the holder on `app.state` to make (a) easier — [research.md](./research.md) R5 records why no new public surface is added for a test
- [ ] T005 [P] [US1] Write the **routes'** tests in `packages/aoa-maxitor/tests/test_api_diagram_routes.py`, per [contracts/routes.md](./contracts/routes.md) § 2. Build the app, load a `DuckDBGraphResource.build_from_json(...)` fixture into `app.state.duckdb_graph`, and drive all six routes with `TestClient`, supplying the query parameters the two that need them require. Assert (a) every route reaches its action — a wrong connection value fails `ConnectionValidator` before the first aspect, which is exactly the regression this test exists for; (b) the payloads match the T001 baseline's *loaded* behaviour (FR-014, SC-001); (c) **every one of the six** reads the **replaced** slot — replace `app.state.duckdb_graph` with a second graph and confirm each route answers from the new one, not the first (FR-005, SC-005). Name the test that asserts (b) `test_routes_with_a_graph_answer_the_recorded_baseline`, and the one that asserts (c) with `replaced_slot` in it — [quickstart.md](./quickstart.md) § 3 and § 4 select them by those words
- [ ] T006 [US1] Run the MVP checkpoint: `uv run pytest packages/aoa-maxitor -q`. Confirm the six routes answer as before with a graph loaded, the new tests pass, and the entire pre-existing suite is still green with **no existing test edited** (SC-011). Deliberately break one route — hand it a second, different connection value — and confirm T005 fails complaining about the connection rather than about JSON; restore. Then record the actual counts in [quickstart.md](./quickstart.md) § 0

**Checkpoint**: US1 alone is the whole point of the feature — the declaration is truthful and Maxitor is out of #215's migration. Nothing yet checks what happens before the first load.

---

## Phase 4: User Story 2 — before the first load, the failure names the situation (Priority: P2)

**Goal**: reading the shared resource when no graph is loaded raises `HandleError` naming the situation and the remedy, in all three slot states, where today it produces a `TypeError` about a per-call factory's return value — and the response a caller receives does not change at all.

**Independent Test**: read the resource with the slot absent, with it empty, and after a successful load; then drive all six routes with nothing loaded and confirm every status and body matches the T001 baseline (quickstart § 1–2).

- [ ] T007 [US2] *(absorbed by T002 — see the note below)* Add the refusal to `_resolve()` in `packages/aoa-maxitor/src/aoa/maxitor/api/duckdb_graph_holder.py`, per [contracts/resource.md](./contracts/resource.md) § 3 and [data-model.md](./data-model.md) E3. When the value read from the slot is `None`, raise `aoa.action_machine.exceptions.HandleError` — the name exported from the package `__init__`. The message must name the **situation** and the **remedy**: that no graph is loaded and that the load endpoint must be called first; `Graph is not loaded: call POST /api/load first.` is the working wording. It must not mention a factory, a return type, a connection wrapper, or any other framework plumbing (C-3.2, FR-008). Because the read is already `getattr(…, "duckdb_graph", None)`, a slot that does not exist yet and a slot that is `None` produce **the same** failure — do not add a second branch for the absent case (FR-007, C-3.3)
**Note on T002 and T007 — the split did not survive implementation.** T002 was written to build the
holder *without* its refusal so that User Story 2 would have code of its own. The module cannot be
written that way and still pass the repository's own type gate: `_resolve` returns whatever the slot
holds, `mypy` runs with `warn_return_any`, and both `-> Any` and a `cast` were tried and rejected —
the first because the two public members then return `Any` from declared types, the second because it
is a lie in the type system about a value that can be `None`. The only honest, type-clean form is the
guard, and the guard *is* the refusal. The holder therefore arrives whole in T002, and T007 is done
with it; what remains of User Story 2 is its tests, T008–T010.

- [ ] T008 [P] [US2] Write the failure tests for the **resource** in `packages/aoa-maxitor/tests/test_api_duckdb_graph_holder.py`, per [contracts/routes.md](./contracts/routes.md) § 3.1–3.2 and § 3.5. Read the resource directly — `TestClient` **cannot** be used here, because the adapter's catch-all middleware intercepts first ([research.md](./research.md) R8). Assert: with `app.state.duckdb_graph = None` the read raises `HandleError` whose message names the unloaded situation and the load endpoint; with the lifespan never run (no attribute at all) it raises the **same** failure, never `AttributeError`; after a successful load no failure is raised; and with nothing loaded the raised failure is not a `TypeError` and its text does not contain `must return BaseResource` (FR-007, FR-008, SC-006)
- [ ] T009 [P] [US2] Write the unloaded-response test for the **routes** in `packages/aoa-maxitor/tests/test_api_diagram_routes.py`, per [contracts/routes.md](./contracts/routes.md) § 3.3–3.4. Drive the routes of an unloaded app with `TestClient(app, raise_server_exceptions=False)` inside a `with` block, so the lifespan has run, and assert each status **and** body against the T001 baseline. **Five of the six are unchanged** — `500 {"detail":"Internal server error"}` for `/list-domains`, `/list-node-types` and `/full-graph`, `422` with the missing-parameter detail for the two that require a query. **The sixth diverges and the divergence is measured, not assumed**: `/list-entities` with no `domain_qualnames` never reads the connection at all, so with a ready resource nothing has a chance to refuse and it answers `200 {"domain_slices":[]}` where it used to answer `500`. Assert the five as passing tests; pin the sixth as a **strict `xfail`** carrying the recorded baseline, with the reason pointing at [research.md](./research.md) R11, so restoring the old answer fails loudly instead of passing silently. Name the passing test `test_routes_without_a_graph_answer_the_recorded_baseline` (the quickstart selects it by `without_a_graph`)
- [ ] T010 [US2] Write the failed-load test in `packages/aoa-maxitor/tests/test_api_diagram_routes.py`, per [contracts/routes.md](./contracts/routes.md) § 4.1. With a graph already loaded, make `POST /api/load` fail — an unreachable service URL is enough, and the mock-free path is to point it at a closed port — and assert that (a) the load answers `422`, and (b) every one of the six routes still reads the graph loaded before it, not a cleared slot and not a half-built one (FR-011, SC-007). Then assert the same app with **nothing** yet loaded answers the named failure after the failed load, so a failed load is not mistaken for an empty one
- [ ] T011 [US2] Run the checkpoint: `uv run pytest packages/aoa-maxitor -q` and re-run T001's six-route baseline driver against the new code. Every status and body must be identical to the recorded before-state, the failure must name the situation in all three slot states, and the pre-existing suite must still be green with no edited test

**Checkpoint**: both stories are independently functional — the declaration is truthful and the unloaded case is legible to whoever debugs it, while a caller sees exactly what it saw before.

---

## Phase 5: *(cancelled)* User Story 3 — the framework's guidance stops recommending this shape

**Cancelled, and the reasoning is in the specification rather than here.** The story asked that
`docs/tutorials/step-17-connections.md` stop telling developers to keep a shared object in an
external holder and read it from inside a per-call factory — which is precisely the shape this
feature deletes from Maxitor, and the reason Maxitor looked that way. The maintainer settled it
directly: **issue #213 does not touch that document.**

The observation was confirmed in the repository and is not lost: it is kept in [spec.md](./spec.md)
as a withdrawn story with its quotation, and withdrawn there as FR-015 and SC-012. No task is
planned, and the chapter keeps its wording until someone decides otherwise in its own scope.

---

## Phase 6: Cross-cutting verification

**Purpose**: the claims that no single story's tests can make — mostly about what the change
**did not** touch.

- [ ] T012 [P] Verify the blast radius of the change. Compare the branch against its base, because by this point every phase is a commit and `git diff` against `HEAD` is empty: `git diff --stat main...HEAD`. The result must show **zero** files under `packages/aoa-action-machine/` (FR-013, SC-010), **zero** edits to the six actions' `@connection` declarations (FR-010), **zero** changes under `packages/aoa-maxitor/client/`, and nothing in `api/routes/load.py` or `api/routes/sidebar.py` (FR-012). The `uv.lock` release-sync commit that already sat on this branch is expected in the diff and is not part of this feature: name it in the report rather than counting it as a violation. Confirm in the same pass that `git diff --name-only main...HEAD -- packages/aoa-maxitor/tests/` lists only the two new test modules, since SC-011 claims no existing test was edited
- [ ] T013 [P] Walk [quickstart.md](./quickstart.md) end to end and reconcile it with what the code actually does. Every command must run as written, every `-k` selector must match a test that exists, every expected figure must match a fresh run, and the baseline table must still be the T001 measurement. Correct the guide where it disagrees with reality — a quickstart that has drifted from the code is the same defect as a failing test

---

## Phase 7: The closing three steps (constitution, Principle VI)

**Purpose**: the constitution reserves **exactly these three tasks, in this order**, and no other task may absorb them. Nothing follows them. The check run comes first of the three and stays valid, because the two steps after it write prose and a runnable example, not the code the run measures; `ruff` and the packaging steps do not inspect either.

- [ ] T014 Run the repository check to zero: `bash scripts/run_checks_with_log.sh` from the repository root; fix every remark it reports — none triaged away, none accepted as known, none left for later; review whatever `ruff check --fix` changed, because the run edits the code (the new module's header, AI-CORE block and docstrings are among what it will reformat). The only two remarks that stay are the Vite chunk-size advisory and LangGraph's pending-deprecation warning
- [ ] T015 Write the documentation, after the code is settled. Two parts, because Principle VI asks for both. **(a) The pages this change owns.** The maintainer ruled `docs/tutorials/step-17-connections.md` out of scope, and a grep of `docs/` and `examples/` confirms that chapter is the only place in the repository that mentions `PerCallConnection` — so no page states the shape this change removes. What is owed is therefore the new module's own documentation: re-read its module header, AI-CORE block and one-line docstrings against Principles III–V once the code has stopped moving, and correct them. **(b) The runnable example, which Principle VI points 4–6 require.** The change introduces cases a reader must be able to reproduce: reading the resource before any load and getting the named failure, reading it after a load, a second load replacing the graph, and two applications staying apart. Each case appears **twice** — as the script `examples/step_26_maxitor/02_api_shared_graph.py` and as the notebook beside it, the same case cell by cell — and the script is executed with the repository's own environment while it is written, so what the reader sees is what it actually printed. The chapter is not touched; the example is a new artefact beside it. Record in the commit message that no page was added, so the omission is a decision on the record
- [ ] T016 Write the changelog last, as one article: **one** piece under `## [Unreleased]` in `packages/aoa-maxitor/CHANGELOG.md`, about what this work created — Maxitor's diagram endpoints now declare the one graph they actually share, instead of declaring a fresh resource per request — in plain words, with what a developer has to know, without technical detail, without a per-file account and without a list of commits. **Ask the maintainer first** whether the framework-level `docs/CHANGELOG.md` also gets a line: Principle VI names that file, while the repository's practice is that `packages/aoa-maxitor/CHANGELOG.md` carries Maxitor changes (#199 did) and `docs/CHANGELOG.md` carries framework-level ones (#196 did). This plan's Constitution Check records that difference rather than resolving it silently. One article either way — never two copies of the same text

---

## What is deliberately not in this spec

Four things surfaced while this feature was specified and planned. None of them is a task here, and each is filed or recorded somewhere with a name:

- **Making the failure visible.** `_CatchAllErrorsMiddleware` (`packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py:527-550`) turns every uncaught exception into `500 {"detail": "Internal server error"}` and **logs nothing**, so the clearer message is readable only where the resource is driven directly. Logging it, or answering with a deliberate status, is a decision about the adapter — and it contradicts the maintainer's decision for this feature that the caller's behaviour must not change ([spec.md](./spec.md), Out of scope; [research.md](./research.md) R8).
- **[#214](https://github.com/bystrovmaxim/aoa/issues/214) — several graphs in one process.** Sessions and per-user state. The holder's shape (one resource, resolving on each read) was chosen so that #214 changes only the source it resolves from.
- **[#215](https://github.com/bystrovmaxim/aoa/issues/215) — a lifetime for per-call resources.** A mandatory `finalize` for mode 2. This feature lands first precisely so Maxitor is not among the declarations that migration has to discover by hand.
- **Rewording `docs/tutorials/step-17-connections.md`.** Withdrawn as User Story 3 above; the maintainer ruled it out of issue #213's scope.

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no dependencies — run the baseline first, or the "unchanged" clauses have nothing to compare against
- **Phase 2 (Foundational)**: needs T001 only for the record; it blocks both user stories
- **Phase 3 (US1)**: needs Phase 2. Produces the feature's whole value on its own
- **Phase 4 (US2)**: needs Phase 2, and in practice follows Phase 3, because the refusal is added to a module US1 already wired in. The two are independently **testable**; they are not independently **writable** in one file
- **Phase 5**: cancelled — nothing to do
- **Phase 6 (verification)**: needs both stories complete
- **Phase 7 (the closing three)**: needs everything else, and nothing follows it

### Within a story

- T003 before T004/T005: the tests observe the wiring the task makes
- T007 before T008/T009/T010: the tests assert the refusal the task adds
- T004 and T005 are different files and may be written in either order; T006 closes the story
- T008 is a different file from T009, so they may be written in either order; T010 extends T009's file and follows it; T011 closes the story

### Parallel opportunities

- T004 `[P]` (resource tests) and T005 `[P]` (route tests) — different modules, neither depends on the other
- T008 `[P]` (resource tests) and T009 `[P]` (route tests) — the same split
- T012 and T013 `[P]` — one inspects the branch diff, the other runs the guide; neither writes code

## Parallel Example

```bash
# User Story 1 — after T003 has wired app.py:
Task: "Resource tests in packages/aoa-maxitor/tests/test_api_duckdb_graph_holder.py"
Task: "Route tests in packages/aoa-maxitor/tests/test_api_diagram_routes.py"

# User Story 2 — after T007 has added the refusal:
Task: "Failure tests in packages/aoa-maxitor/tests/test_api_duckdb_graph_holder.py"
Task: "Unloaded-response tests in packages/aoa-maxitor/tests/test_api_diagram_routes.py"
```

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 — record the baseline
2. Phase 2 — build the holder
3. Phase 3 — wire the six routes and prove the sharing
4. **Stop and validate**: with a graph loaded, all six routes answer exactly as before and read one object. This alone delivers the feature's purpose: the declaration is true, and Maxitor is out of #215's way

### Then

5. Phase 4 — the unloaded failure, and the proof that a caller sees nothing new
6. Phase 6 — the blast-radius and guide checks
7. Phase 7 — the closing three, in order and last

### One phase, one commit

Per the repository's rule, each phase is a commit of its own, written in English, and the closing three are three separate commits in the order given. Nothing is committed without an explicit instruction in the current conversation.

## Notes

- `[P]` marks tasks that touch different files or are independent of an incomplete task. Tasks that extend the same file are never marked `[P]`, which is why the two test modules are split by subject
- The whole change lives under `packages/aoa-maxitor/`, plus one runnable example under `examples/step_26_maxitor/`; a diff outside that is a defect, not a surprise
- `TestClient` can never observe the raised `HandleError` — the adapter's catch-all intercepts first. The failure is asserted on the resource; the caller's response is asserted through the app. Both halves are needed and neither substitutes for the other
- Nothing about the six route registrations is introspectable after `create_app()` returns, because the adapter holding the route records is discarded. The "one object, declared once" claim is therefore proved by counting real constructions of `DuckDBGraphHolder` during the real build, not by reading the registrations ([research.md](./research.md) R10)
