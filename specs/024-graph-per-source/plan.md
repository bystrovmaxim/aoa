# Implementation Plan: One Graph per Source, Named by Every Request

**Branch**: `feature/issue-214-graph-per-source` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/024-graph-per-source/spec.md` (issue #214)

## Summary

Maxitor's one shared graph slot becomes a **graph store keyed by source**. Every graph read names its source as a `source` query parameter; a middleware turns that parameter into the request's graph before the adapter runs — building it on a cold read, once per source however many readers arrive — and refuses a missing or unbuildable source with a named reason. `DuckDBGraphHolder` stays one ready resource and resolves the request's graph instead of the application's. `POST /api/load` becomes "rebuild this source". Graphs unread for an hour are removed, at most 50 are held, and nothing is ever re-checked on a timer. The client sends its source with every read, opens deep links without reloading, and gains a "Reload from service" button.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.7 / React 19 (client)

**Primary Dependencies**: FastAPI + Starlette, `aoa-fastapi-adapter`, `aoa-action-machine`, DuckDB, httpx; client: Vite 6, MUI 6. New client dev dependencies: `vitest`, `jsdom`, `@testing-library/react` (research R7).

**Storage**: in-memory DuckDB per built graph; the graph store is a process-local map

**Testing**: pytest (`packages/aoa-maxitor/tests`), `fastapi.testclient` / `httpx.AsyncClient` over ASGI for concurrency; vitest for the client

**Target Platform**: one uvicorn process (`maxitor-api`), Linux container behind nginx-proxy on the stand

**Project Type**: web application — FastAPI backend serving a React SPA

**Performance Goals**: a burst of 300 simultaneous opens of one deep link costs one download and one build with 0 errors (SC-008); a repeat open costs no download and no build (SC-002)

**Constraints**: one event loop; a built graph is ≈ 48 MiB (measured, research); the DuckDB build (0.13–0.6 s) runs on the event loop

**Scale/Scope**: up to 50 graphs per process by default (≈ 2.4 GiB worst case); six diagram routes, the sidebar route, the load route; four client API modules and `App.tsx`

## Constitution Check

*GATE: checked before Phase 0 and again after Phase 1.*

| Principle | How this plan meets it | Status |
|---|---|---|
| I. The maintainer decides | Every phase in `tasks.md` ends in a commit **prepared**, not made; nothing is committed, pushed or opened as a PR without an instruction in the conversation. | Pass |
| II. English | All code, docstrings, tests, examples, commit messages in English; Russian only in `*.ru_draft.md`, which Git ignores. | Pass |
| III. Module headers | New modules (`graph_store.py`, `graph_source_middleware.py`) open with the path line and a `Name — purpose.` docstring with `PURPOSE` and `ARCHITECTURE / DATA FLOW`; `duckdb_graph_holder.py`'s header is rewritten to the new data flow. | Pass |
| IV. AI-CORE blocks | `GraphStore`, `GraphEntry`, `GraphSourceMiddleware` carry `ROLE` / `CONTRACT` / `INVARIANTS`; the holder's block is updated ("one per application; holds no graph; resolves the request's graph"). No block on a method. | Pass |
| V. Short docstrings | Every new class, function and method carries a one-line docstring. | Pass |
| VI. Tail | Three final tasks, in order: check run to zero, documentation (every case as a script and a notebook), changelog article. | Pass |
| Check run | The run gains one step, `npm test` for the client; the script is part of the change. The two accepted remarks stay as they are. | Pass |

Post-design re-check: the design adds no new package and no cross-package dependency (`check_package_boundaries.py` unaffected); the adapter and the action machine are not changed. **Pass.**

## Project Structure

### Documentation (this feature)

```text
specs/024-graph-per-source/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R8 and the measurements
├── data-model.md        # GraphStore, GraphEntry, request binding
├── quickstart.md        # end-to-end validation
├── contracts/
│   └── graph-source-http.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
packages/aoa-maxitor/src/aoa/maxitor/api/
├── app.py                       # builds the store, installs the middleware, reads MAXITOR_MAX_GRAPHS / MAXITOR_GRAPH_IDLE_SECONDS / MAXITOR_MAX_CONCURRENT_BUILDS; installs the middleware inside CORS; health counters
├── graph_store.py               # NEW — GraphStore, GraphEntry, GraphBuildError
├── graph_source_middleware.py   # NEW — source → request's entry; 400 / 422 / 503 with CORS headers
├── duckdb_graph_holder.py       # resolves the request's entry, not app.state
└── routes/
    ├── load.py                  # POST /api/load → store.reload(source)
    └── sidebar.py               # reads the request's entry

packages/aoa-maxitor/tests/
├── test_api_graph_store.py              # NEW — single flight, capacity, idle removal, failures
├── test_api_graph_source_middleware.py  # NEW — 400, 422, 503, two clients, one graph per request
├── test_api_graph_burst.py              # NEW — 300 simultaneous opens, one build
├── test_api_diagram_routes.py           # updated to name the source
└── test_api_duckdb_graph_holder.py      # updated to the request binding

packages/aoa-maxitor/client/
├── package.json                 # vitest, jsdom, @testing-library/react; "test" script
├── vite.config.ts               # test environment
└── src/
    ├── api/client.ts            # setActiveSource, graphApiUrl
    ├── api/*.ts                 # every graph read through graphApiUrl
    ├── app/App.tsx              # deep link reads only; typed source reloads; reload button wiring
    ├── components/navigation/LeftSidebar/…   # "Reload from service" control
    ├── components/navigation/LeftSidebar/hooks/useSidebarPayload.ts  # no fetch without a source
    └── **/*.test.ts(x)          # NEW

scripts/run_checks_with_log.sh    # + "Maxitor client: unit tests"

examples/step_26_maxitor/
└── 02_api_graph_per_source.py / .ipynb   # replaces 02_api_shared_graph.*

docs/tutorials/step-26-maxitor.md (+ .ru_draft.md)
packages/aoa-maxitor/README.md (+ .ru_draft.md)
docs/CHANGELOG.md
```

**Structure Decision**: the existing Maxitor package layout; the two new modules sit beside `duckdb_graph_holder.py` in `aoa.maxitor.api`, because they belong to the HTTP boundary, not to the diagram model.

## Phases (one commit each)

Every commit leaves the application working. That is why the client starts sending its source (phase 2) **before** the server requires it (phase 4): today's server ignores an unknown query parameter, so phase 2 changes nothing visible, and phase 4 then finds every read already naming its source.

1. **Specification artifacts** — `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`.
2. **The client sends its source** — vitest setup and check-run step, `graphApiUrl`, every graph read carries `source`, no sidebar read without a source (FR-016). Deep links still call `POST /api/load` here, because the old server cannot build on a read.
3. **Graph store** — `graph_store.py` with its unit tests (US5, FR-001–FR-006, FR-011, FR-013's cancellation rule).
4. **Every read names its source** — middleware, holder, sidebar route, `create_app` wiring, stale "POST /api/load" messages, updated route and holder tests (US1, FR-007–FR-010).
5. **`POST /api/load` rebuilds one source** — load route and tests (FR-014, FR-015).
6. **A burst on one link** — the 300-open test (US3, FR-012, FR-013, SC-008).
7. **The client opens deep links without reloading, and can reload on purpose** — deep link reads only, typed source, leaving, "Reload from service" (US2, US4, FR-017–FR-023).
8. **Check run taken to zero.**
9. **Documentation** — example script + notebook, tutorial, README (and their `.ru_draft.md`).
10. **Changelog** — one article.

## Risks recorded

- **Memory**: 50 graphs ≈ 2.4 GiB worst case (research). The maintainer kept the default of 50 because memory is taken per built graph, not reserved up front. A dropped graph's memory is not returned to the system on macOS, only reused, so the process size is the high-water mark of graphs held at once. Reducing the indexes behind 38 MiB of each graph, and measuring the behaviour on Linux, is #268. The idle timeout is an hour, longer than a burst lasts, so on the stand the cap of 50 — not idling — is what bounds memory.
- **Eviction by many sources**: without an allowlist (out of scope) anyone can name 50 sources and push out everyone else's graphs; it costs readers one rebuild each and the process its memory, never a wrong graph. Builds are bounded at 4 at a time, so at most 4 graphs are being built on top of the up to 50 held.
- **Slots held by unreachable sources**: a download may take its full 15-second timeout, so four bad addresses can hold every build slot for 15 s and make cold reads of all sources wait. A failed source is remembered for 10 s and a read waiting 30 s for a slot gets a 503, so the stand answers instead of hanging; many distinct bad addresses can still fill the slots. Accepted consciously; the allowlist is the fix and is out of scope.
- **Open tabs during the deploy**: a tab loaded before phase 4 is deployed keeps its old code until reloaded; from phase 2 on, that code already sends `source`, so only tabs older than phase 2's deploy see the 400.
- **A busy 503 is visible**: under a cold burst the stand may answer "Maxitor is busy" for a read that waited 30 s for a build slot. The client keeps the source and the diagram and retries, so the user sees a short wait, never the "AOA Service URL" prompt for a source that is merely busy (FR-029).
- **Event loop**: a cold build blocks other requests for 0.13–0.6 s once per source (research R5).
- **OpenAPI**: the adapter's generated schema does not list `source`, because the middleware reads it; the contract in `contracts/graph-source-http.md` documents it.

## Complexity Tracking

No constitution violations to justify.
