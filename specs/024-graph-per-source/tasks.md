# Tasks: One Graph per Source, Named by Every Request

**Input**: Design documents from `specs/024-graph-per-source/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/graph-source-http.md, quickstart.md

**Tests**: Required — the success criteria (SC-001–SC-008) are proved by tests, and the constitution's adversarial rule needs a test that fails when the behaviour is broken.

**Organization**: one phase = one commit, in the order of plan.md "Phases". Every commit leaves the application working: the client sends its source (Phase 2) before the server requires it (Phase 4). Phases are labelled with the user stories they deliver (US1–US5 from spec.md). The three tail tasks (check run, documentation, changelog) are reserved and in that order per constitution VI. Every commit is **prepared and shown**, never made without the maintainer's instruction (constitution I); every commit message references `(#214)`.

**Test doubles**: tests never add a parameter to production code. They replace `app.state.graph_store` with a `GraphStore` over a stub builder; the middleware reads the store from `scope["app"].state.graph_store` at request time (research R3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no shared dependency)
- **[Story]**: maps the task to a user story (US1–US5)
- Every description carries an exact file path.

---

## Phase 1: Setup — specification artifacts (commit 1)

**Purpose**: a green baseline and the design documents.

- [x] T001 Confirm `feature/issue-214-graph-per-source` is checked out and run `uv run pytest packages/aoa-maxitor/tests -q` as the green baseline; record the pass count: **154 passed, 1 skipped, 1 xfailed in 2.71 s**.
- [x] T002 Commit 1 with `specs/024-graph-per-source/` (spec, checklist, plan, research, data model, contract, quickstart, tasks), message `docs(spec): specify one graph per source, named by every request (#214)`. `.specify/feature.json` stays out: `.specify/.gitignore` ignores it and it already names this feature directory.

---

## Phase 2: The client sends its source (commit 2) · US1, US2

**Goal**: every graph read from the browser already names its source, so the server phase that requires it breaks nothing. Today's server ignores the extra query parameter.

**Independent Test**: `npm test` in `packages/aoa-maxitor/client`; the app still works against today's server.

- [x] T003 Add `vitest`, `jsdom` and `@testing-library/react` as dev dependencies and a `"test": "vitest run"` script in `packages/aoa-maxitor/client/package.json` (lockfile updated), with the test environment in `packages/aoa-maxitor/client/vite.config.ts`.
- [x] T004 Add a step `Maxitor client: unit tests` running `(cd packages/aoa-maxitor/client && npm test)` right after the client build step in `scripts/run_checks_with_log.sh`.
- [x] T005 [US1] In `packages/aoa-maxitor/client/src/api/client.ts` add `setActiveSource(url: string | null)` and `graphApiUrl(path, query?)`, which appends `source=<active source>` and throws when no source is active; one-line comments on both.
- [x] T006 [P] [US1] Route every graph read through `graphApiUrl`: `packages/aoa-maxitor/client/src/api/fullGraph.ts`, `sidebar.ts`, and the modules behind list-domains, list-entities, lifecycle-finite-automaton and domain-use-case-diagram in `packages/aoa-maxitor/client/src/api/`; `load.ts` keeps its body.
- [x] T007 [US1] In `packages/aoa-maxitor/client/src/app/App.tsx` set the active source **synchronously during the first render**, where `initialLinkRef` is read (not in an effect: `useSidebarPayload`'s mount effect is declared earlier and runs first), and in `handleLoaded` and the popstate path; clear it in `handleReset`. Deep links still call `loadGraph` in this phase.
- [x] T008 [US2] In `packages/aoa-maxitor/client/src/components/navigation/LeftSidebar/hooks/useSidebarPayload.ts`: no fetch on mount without an active source.
- [x] T009 [US1] Create `packages/aoa-maxitor/client/src/api/client.test.ts`: `graphApiUrl` appends the URL-encoded source, keeps the route's own query parameters, and throws without an active source; a parser test that `?source=<url>&view=full-graph` still yields that source and view (FR-022); and an address containing `&`, `+`, `%2F` and a space comes back unchanged after `graphApiUrl`'s encoding is decoded (FR-027).
- [x] T010 [US2] Create `packages/aoa-maxitor/client/src/app/App.test.tsx` (fetch stubbed): opening a deep link makes its **first** request a sidebar read that already carries the link's source, sends exactly one `POST /api/load`, and sends no read without a source (FR-016). In this phase the open reads the sidebar twice — the mount read and the one after the load; phase 7 drops the load and leaves one.
- [x] T011 Adversarial check: drop `source` from `graphApiUrl`; let it build a URL without an active source; build the query by string concatenation without encoding; set the active source in an effect instead of the first render. Each time the matching test fails; restore.
- [x] T012 Prepare commit 2: `feat(maxitor): the client names its source on every graph read (#214)`.

---

## Phase 3: Foundational — the graph store (commit 3) · US5

**Goal**: a store that holds graphs by source, builds each once, removes idle ones and stays bounded.

**Independent Test**: the store's unit tests alone, with a stub builder and an injected clock; no HTTP.

- [x] T013 [US5] Create `packages/aoa-maxitor/src/aoa/maxitor/api/graph_store.py`: module header (constitution III), `GraphEntry` (`source`, `graph`, `sidebar`, `last_read`; "`graph` and `sidebar` come from the same build"), `GraphBuildError(reason)`, and `GraphStore(builder, *, max_graphs=50, idle_seconds=3600, max_concurrent_builds=4, clock=time.monotonic)` with `acquire(source)`, `reload(source)`, `sweep()` exactly as in `data-model.md` §GraphStore: single flight per source, the build running as its own task awaited through `asyncio.shield` ("a waiter that is cancelled stops waiting, but the build goes on for the others and its entry is stored"); "a failed build raises `GraphBuildError(reason)` to every waiter and stores nothing"; eviction of the least recently read entry beyond `max_graphs`; removal of entries unread for `idle_seconds` on every access; `reload` keeps the held entry when its build fails; every build, from `acquire` or `reload`, runs inside an `asyncio.Semaphore(max_concurrent_builds)` (default 4) taken **inside the build task, after any wait on `in_flight`** (a caller that holds a slot while awaiting another build deadlocks); a build that waits 30 s for a slot raises `GraphStoreBusyError`; a failed build is remembered 10 s in `failures` ("`acquire` within that window raises the same `GraphBuildError` without building; `reload` ignores it"; only `GraphBuildError` is recorded, never `GraphStoreBusyError`); one build in flight per source of any kind ("`reload` that finds `in_flight[source]` awaits it, then starts its own build"); `held`, `building` and `queued` report the counts. AI-CORE blocks on `GraphEntry` and `GraphStore`; one-line docstrings on every method.
- [x] T014 [US5] Add `build_graph_entry(machine, source)` in `packages/aoa-maxitor/src/aoa/maxitor/api/graph_store.py`, running `LoadAOAServiceAction` then `GetLeftMenuSidebarDataAction` the way `packages/aoa-maxitor/src/aoa/maxitor/api/routes/load.py` does today, and turning any failure into `GraphBuildError(str(exc))` (research R5).
- [x] T015 [US5] Create `packages/aoa-maxitor/tests/test_api_graph_store.py`: two sources side by side; 10 concurrent `acquire` of one cold source → builder called once, all 10 get the same entry; the first waiter cancelled mid-build → the other 9 still get the entry and it is stored; a failed build → every waiter gets `GraphBuildError`, nothing stored, and the next `acquire` tries again only after the 10 s window (clock moved); capacity → the least recently read entry is the one removed; an entry unread for `idle_seconds` is removed and one read within it is kept (clock moved, no sleeping); `reload` replaces on success and keeps the old entry on failure; an entry acquired before its removal stays usable by its holder; 20 different cold sources acquired at once → the builder never runs more than 4 at the same time and all 20 are answered (SC-009); `held`, `building` and `queued` match the store's state during and after builds; a failed source is not downloaded again within 10 s and is tried again after; `reload` called while a cold `acquire` build of the same source runs → the reload's entry is the one stored, the earlier build never overwrites it (SC-010); a build that cannot get a slot within the wait limit raises `GraphStoreBusyError` (the test shortens the module's wait constant with `monkeypatch`); after a `GraphStoreBusyError` the next `acquire` of that source builds again (busy is never remembered as a failure).
- [x] T016 Adversarial check, one break at a time: start a build per waiter; await the build unshielded; never sweep; evict the newest; remove the semaphore; let `reload` start without awaiting the in-flight build; take the build slot before awaiting `in_flight` (the reload-during-build test must hang and be caught by its timeout); drop the failure memory; remember a busy refusal as a failure. Confirm the matching T015 test fails and no other does; restore.
- [x] T017 Prepare commit 3: `feat(maxitor): keep built graphs in a store keyed by source (#214)`.

**Checkpoint**: the store exists and is proved; nothing uses it yet.

---

## Phase 4: User Story 1 — every read names its source (commit 4) · US1, US2 (server), US5 🎯 MVP

**Goal**: each graph read is answered from the graph of the source it names, built on a cold read; two users can no longer see each other's graph.

**Independent Test**: two `TestClient` sessions on one app, reading two sources in interleaved order; every answer belongs to its own source.

- [x] T018 [US1] Create `packages/aoa-maxitor/src/aoa/maxitor/api/graph_source_middleware.py`: a pure ASGI middleware (research R2) for paths starting with `/api/v1/` and equal to `/api/sidebar`, letting `OPTIONS` requests pass through untouched; reads the `source` query parameter; missing or blank → **400** `{"detail": "Missing query parameter 'source': name the graph-json URL this read is for."}`; takes the store from `scope["app"].state.graph_store`; `GraphBuildError` → **422** `{"detail": <reason>}`; `GraphStoreBusyError` → **503** with header `Retry-After: 5` and `{"detail": "Maxitor is busy building other graphs; try again shortly."}`; otherwise binds the acquired `GraphEntry` to a module-level `ContextVar` for the request and resets it after the response. Module header, AI-CORE block on the middleware class, a `current_graph_entry()` accessor with its one-line docstring.
- [x] T019 [US1] Rewrite `packages/aoa-maxitor/src/aoa/maxitor/api/duckdb_graph_holder.py`: `_resolve()` returns the bound entry's `graph` via `current_graph_entry()`; outside a bound request it raises `HandleError` naming the missing binding (not `POST /api/load`); the constructor takes no `app`. Rewrite the module header's PURPOSE and data-flow diagram and the AI-CORE block ("one per application; holds no graph; resolves the graph bound to the current request").
- [x] T020 [US1] Update `packages/aoa-maxitor/src/aoa/maxitor/api/routes/sidebar.py`: `GET /api/sidebar` answers `sidebar_payload(current_graph_entry().sidebar)`; remove the "nothing loaded → empty payload" branch (contract: a read without a source is a 400).
- [x] T021 [US1] Update `packages/aoa-maxitor/src/aoa/maxitor/api/app.py`: build `GraphStore(build_graph_entry bound to the machine, …)` from `MAXITOR_MAX_GRAPHS` (default 50), `MAXITOR_GRAPH_IDLE_SECONDS` (default 3600) and `MAXITOR_MAX_CONCURRENT_BUILDS` (default 4) — "a positive integer" / "a positive number", otherwise refuse to start with a `ValueError` naming the variable; keep it on `app.state.graph_store`; install `GraphSourceMiddleware` **inside** `CORSMiddleware` (added before it, since the last added middleware is the outermost), so its 400, 422 and 503 carry the CORS headers, with `expose_headers=["Retry-After"]` so a client on another origin can read the pause; `GET /api/health` answers `{"status": "ok", "graphs_held": …, "builds_running": …, "builds_queued": …}`; remove the `duckdb_graph` and `sidebar_data` slots from `lifespan`; construct the holder without `app`.
- [x] T022 [US1] Replace the stale hint "Ensure the AOA service graph is loaded via POST /api/load." in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/get_lifecycle_finite_automaton_action.py:143` with one that names the source the read was for, and update every test that asserts the old wording (`packages/aoa-maxitor/tests/test_api_duckdb_graph_holder.py:180` and any found by `grep -rn "api/load" packages/aoa-maxitor/tests`).
- [x] T023 [US1] Update `packages/aoa-maxitor/tests/test_api_diagram_routes.py` and `packages/aoa-maxitor/tests/test_api_duckdb_graph_holder.py` to the new contract: reads carry `source`, `app.state.graph_store` is replaced by a store over a stub builder that serves fixtures by source; keep every existing payload assertion.
- [x] T024 [US1] Create `packages/aoa-maxitor/tests/test_api_graph_source_middleware.py`: no `source` → 400 with the exact detail; an unbuildable source → 422 with the reason, nothing stored; client A on X and client B on Y, at least 50 interleaved reads in random order → 100 % own-source answers (SC-001); a read for X right after Y was loaded answers from X (FR-021, server side); one request whose action queries the graph several times while the same source is reloaded mid-request → every query answered from the first graph (FR-007); a cold read builds and answers; after idle removal the next read rebuilds and answers 200 (US5 scenario 2, SC-006); invalid `MAXITOR_MAX_GRAPHS` / `MAXITOR_GRAPH_IDLE_SECONDS` / `MAXITOR_MAX_CONCURRENT_BUILDS` → `create_app()` raises naming the variable; a 422, a 400 and a 503 answered to a request with an `Origin` header carry `Access-Control-Allow-Origin` (FR-026); an `OPTIONS` preflight to a graph read is answered by CORS, not refused for a missing source; `GET /api/health` reports the held, running and queued counts (FR-028); a busy store answers 503 with `Retry-After: 5` and the exact detail, and the answer to a request with an `Origin` header carries `Access-Control-Expose-Headers: Retry-After` (FR-026); the six diagram routes keep their own parameters and answers.
- [x] T025 Adversarial check: resolve from one shared entry instead of the bound one (the old defect) → the two-client test fails; resolve per query instead of per request → the FR-007 test fails; drop the 400 → the missing-source test fails; install the middleware outside CORS → the CORS test fails. Restore after each.
- [x] T026 Prepare commit 4: `feat(maxitor): every graph read names its source (#214)`.

**Checkpoint**: the defect of issue #214 is gone; the client of Phase 2 already works with it (deep links still reload, which is harmless).

---

## Phase 5: User Story 4 (server) — `POST /api/load` rebuilds one source (commit 5) · US4

**Goal**: an explicit reload rebuilds the named source and nothing else.

**Independent Test**: reload Y while a client reads X; X is unchanged, Y is rebuilt; a failing reload of Y keeps Y's previous graph.

- [x] T027 [US4] Rewrite `packages/aoa-maxitor/src/aoa/maxitor/api/routes/load.py`: `POST /api/load` calls `request.app.state.graph_store.reload(body.service_url)`; success → 200 `{"status": "ok"}`; `GraphBuildError` → 422 `{"detail": reason}`; `GraphStoreBusyError` → 503 with `Retry-After: 5` and the busy detail, the source's entry left as it was; request and response shapes unchanged. Update the module docstring.
- [x] T028 [US4] Create `packages/aoa-maxitor/tests/test_api_load_route.py`: reload of Y does not change a reader of X; reload replaces the held Y with a fresh build (builder called again); a failing reload keeps the previous Y and answers 422; the existing unreachable-service tests in `packages/aoa-maxitor/tests/test_api_diagram_routes.py` still pass; an address containing `&`, `+`, `%2F` and a space, read through `?source=` (URL-encoded) and reloaded through `POST /api/load`, is one key: the store holds one entry and the reload replaces it (FR-027).
- [x] T029 Adversarial check: make `reload` clear the whole store → the "X unchanged" test fails; make a failed reload drop the held entry → the "keeps previous Y" test fails. Restore.
- [x] T030 Prepare commit 5: `feat(maxitor): POST /api/load rebuilds only the source it names (#214)`.

---

## Phase 6: User Story 3 — a burst of readers on one link (commit 6) · US3

**Goal**: 300 simultaneous opens of one deep link cost one download and one build, with no error; a held graph is never re-checked on a timer.

**Independent Test**: the burst test alone.

- [x] T031 [US3] Create `packages/aoa-maxitor/tests/test_api_graph_burst.py`: `httpx.AsyncClient` over `ASGITransport` on `create_app()`, `app.state.graph_store` replaced by a store over a counting stub builder that sleeps briefly so the requests overlap; fire 300 concurrent `GET /api/sidebar?source=X` and 300 `GET /api/v1/full-graph?source=X`; assert 600 successes, 0 errors, one build (SC-008, SC-003). Then, with the store's clock moved one hour ahead and `idle_seconds` set above that, one more read → 0 further builds (SC-002, FR-012).
- [x] T032 Adversarial check: disable single flight → the build count exceeds 1 and the test fails; add a re-download after any time → the SC-002 assertion fails. Restore.
- [x] T033 Prepare commit 6: `test(maxitor): a burst on one link builds its graph once (#214)`.

---

## Phase 7: User Stories 2 and 4 (client) — deep links read, a button reloads (commit 7) · US2, US4

**Goal**: deep links read without reloading; a typed source reloads; leaving sends nothing; a "Reload from service" button rebuilds the current source.

**Independent Test**: `npm test` in `packages/aoa-maxitor/client`, then the browser steps of `quickstart.md` §3.

- [x] T034 [US2] In `packages/aoa-maxitor/client/src/app/App.tsx`: a deep link sets the active source and reads, with no `loadGraph`; a failed sidebar read (422) falls back to the "AOA Service URL" prompt as today (FR-023); a typed source keeps its one `loadGraph`; `handleReset` sends nothing.
- [x] T035 [US4] Add the "Reload from service" control in the sidebar next to the current source (`packages/aoa-maxitor/client/src/components/navigation/LeftSidebar/`): shown only while a source is open; on click one `loadGraph(current)`, then the sidebar fetched again and the diagram workspace remounted through a reload counter in its `key` in `App.tsx`; URL and selected diagram kept; disabled while running; a failure shown without clearing the diagram. Update the component's `README.md` (the check run requires one beside `index.ts`).
- [x] T036 [US2] Extend `packages/aoa-maxitor/client/src/app/App.test.tsx`: a deep link sends no `POST /api/load` and its first diagram read carries the link's source (FR-021); a deep link to a source whose sidebar read answers 422 shows the prompt; a deep link whose sidebar read answers 503 keeps the source and the diagram, reports Maxitor as busy and retries, and never shows the prompt (FR-029); with fake timers, two 503 in a row give exactly two further tries, the first no sooner than 5 s and the second no sooner than 10 s after it, and later pauses never exceed 30 s; a page with two busy reads keeps one retry loop, not two; a 503 on the "Reload from service" button is shown and not retried; a typed source sends exactly one `POST /api/load`; the button sends exactly one for the current source, then refetches the sidebar and the diagram, and keeps the URL; leaving sends nothing.
- [ ] T037 Adversarial check: call `loadGraph` on a deep link → its test fails; make the button reload twice → its test fails; let leaving send a request → its test fails; treat a 503 like a 422 (fall back to the prompt) → the busy test fails; retry a 503 at once → the retry-timing test fails; drop `expose_headers` → the CORS-expose test fails; retry a busy reload → the button test fails. Restore. Then run `quickstart.md` §3 in the browser and record the network log of each step.
- [x] T038 Prepare commit 7: `feat(maxitor): deep links read without reloading, and a button reloads the source (#214)`.

---

## Phase 8: Closing check run (commit 8)

- [x] T039 Run `bash scripts/run_checks_with_log.sh` and fix every remark until it is clean (the two accepted remarks stay); prepare commit 8 with whatever the run changed: `chore: take the check run to zero (#214)`.

---

## Phase 9: Documentation (commit 9)

- [ ] T040 Replace `examples/step_26_maxitor/02_api_shared_graph.py` and `.ipynb` with `examples/step_26_maxitor/02_api_graph_per_source.py` and `.ipynb`, showing every case of the contract with the real printed output: two sources side by side, a cold read, 400 without a source, 422 for an unbuildable source, 503 when no build slot frees within the wait limit, an explicit reload, a failed reload keeping the old graph, idle removal and rebuild, capacity eviction, one build for a burst, a reader leaving during a build. Run both while writing them.
- [ ] T041 Update `docs/tutorials/step-26-maxitor.md` and `packages/aoa-maxitor/README.md` (the API list with `source`, the loading section, the three configuration variables, the health counters, the "Reload from service" button, the link to the new example) and their `.ru_draft.md` counterparts; replace every remaining reference to `02_api_shared_graph` outside `specs/`.
- [ ] T042 Prepare commit 9: `docs(maxitor): document one graph per source with runnable examples (#214)`.

---

## Phase 10: Changelog (commit 10)

- [ ] T043 Write one article in `docs/CHANGELOG.md` about what this work created, in plain words and with the nuances a user needs (deep links unchanged, the reload button, removal after an hour unread, the 50-graph limit, the limit of four builds at once, and their settings), without technical detail; prepare commit 10: `docs(changelog): one graph per source (#214)`.

---

## Dependencies & Execution Order

- Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10.
- Phase 2 needs nothing from the server. Phase 4 needs the store (Phase 3) and relies on Phase 2 so that no commit leaves the client without a source. Phase 5 needs Phase 4's wiring; Phase 6 needs Phases 4–5; Phase 7 needs the cold read of Phase 4 (a deep link may only stop reloading once a read can build).
- Within Phase 2, T006 touches several API modules independently and can run in parallel; T007–T010 build on T005.

## Parallel Example: Phase 2

```text
T006 fullGraph.ts · sidebar.ts · the four diagram API modules — one edit each, no shared file
```

## Implementation Strategy

- **MVP**: Phases 1–4. After commit 4 the server no longer mixes users' graphs and builds on a cold read, and the client of commit 2 already names its source.
- **Complete**: after Phase 7 the cache, the burst guarantee, deep links without reload and the reload button are in place; the tail (Phases 8–10) closes the change.
