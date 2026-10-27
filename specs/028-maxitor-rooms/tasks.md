# Tasks: Maxitor Rooms — Looking at One Service Together

**Input**: Design documents from `specs/028-maxitor-rooms/`

**Prerequisites**: plan.md, spec.md (with clarifications of 2026-10-27), research.md (R1–R12), data-model.md, contracts/ (websocket-adapter, room-protocol, room-actions, http, layout-determinism), quickstart.md, mockup/index.html

**Tests**: Required. The spec asks for a guard test and a golden hash (FR-005), a check-run step across engines (FR-006) and testable acceptance criteria throughout; the house rule makes verification adversarial — for each test, a break that makes exactly that test fail, then a restore. Python tests run in `uv run pytest`; client tests are vitest files under jsdom, executed by the check run (`npm test`), so they must be fast and deterministic.

**Organization**: one phase = one commit, in the order of plan.md "Phases" (plus commit 1 for the design documents and a split of following into two commits to match the issue). Each phase names the user story it delivers (US1–US11 of spec.md). The three tail tasks — check run, documentation, changelog — are reserved and come last, in that order (constitution VI). Every commit is **prepared and shown**, never made without the maintainer's instruction (constitution I). Every commit message ends with `(#271)`.

**The architectural rule** (research R1, maintainer 2026-10-27): no hand-written route, no decision in a middleware, adapter or timer, no store or service reached outside a resource. A task that cannot be done under it stops and is reported, never worked around. Older violations are #278 and are not touched, except #278's phase 3 (`LoadAOAServiceAction` downloading through `GraphSourceGateway`), which T029 does here.

**Issue checkboxes**: issue #271 §14 lists 14 phases, each ticked with its sha when its commit lands (`gh issue edit 271`). Mapping: commit 2 → issue phase 1; commit 3 → 2; commit 4 → 3; commits 6 and 7 → 4 (ticked after commit 7); commit 12 → 5; commits 5 and 8 → 6 (ticked after commit 8); commit 9 → 7; commit 10 → 8; commit 11 → 9; commit 13 → 10; commit 14 → 11; commit 15 → 12; commit 16 → 13; commits 17–19 → 14 (ticked after commit 19). Commit 1 has no box.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story the task serves (US1–US11)
- Every description carries an exact file path. Every new Python module opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` (constitution III); every new public class carries an AI-CORE block (IV); every class, function and method a one-line docstring (V).
- A `README.md` beside each new `components/*/` or `rooms/*/` folder is required by the check run; it states only what the component is and where it is used. Behaviour and cases are documented in T103, after the code is settled (constitution VI.2).

---

## Phase 1: Setup — design documents (commit 1)

**Purpose**: a green baseline and the specification in history.

- [X] T001 Confirm `feature/issue-271-maxitor-rooms` is checked out; run `uv run pytest packages/aoa-maxitor/tests packages/aoa-fastapi-adapter/tests -q` and, in `packages/aoa-maxitor/client`, `npm ci && npm test && npm run build`; record the pass counts here as the green baseline. Baseline 2026-10-27: **aoa-maxitor 237 passed, 1 skipped** (5.9 s) and **aoa-fastapi-adapter 161 passed** (0.8 s), each run on its own as the check run does (`uv run --extra dev pytest packages/<package>/tests/`; both packages name their test package `tests`, so one combined run fails at collection); client **64 passed** in 10 files (vitest, 4.4 s); `vite build` succeeded, its only remark the accepted chunk-size advisory.
- [X] T002 Prepare commit 1 with `specs/028-maxitor-rooms/` (spec, checklist, mockup, plan, research, data model, contracts, quickstart, tasks; the `*.ru_draft.md` files stay out, `.gitignore` ignores them): `docs(spec): specify Maxitor rooms, fresh graphs and graphs kept until the limit (#271)`. Committed as `050cebd6`.

---

## Phase 2: The same full-graph layout everywhere (commit 2) · US1

**Goal**: equal input gives bit-identical full-graph positions on every engine and screen size (FR-001 … FR-005).

**Independent Test**: `npm test` passes the guard, golden and spiral tests; the page shows a `data-layout-hash` on every viewer's diagram element.

- [X] T003 [P] [US1] Copy the frozen reference graph `specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz` to `packages/aoa-maxitor/tests/fixtures/ref-graph-2026-10-26.json.gz` and save Maxitor's full-graph answer for it (`GET /api/v1/full-graph?source=…`, the server serving the fixture as in `quickstart.md`) as `packages/aoa-maxitor/client/src/components/diagrams/FullGraphViewer/__fixtures__/full-graph-ref.json`; these are the inputs of every layout test. Done: the gz copied; the saved answer (440 nodes, 545 edges) is byte for byte #245's `full-graph-ref.json`.
- [X] T004 [P] [US1] Create `packages/aoa-maxitor/client/src/components/diagrams/FullGraphViewer/initialPositions.ts`: `initialPositions(nodeIds: string[], radius: number): Record<string, [number, number]>` — node *i* at `radius · Math.sqrt(0.5 + i)`, its unit vector obtained from the previous one by multiplying with the literal constants `GOLDEN_COS` and `GOLDEN_SIN` (cos and sin of π·(3 − √5), written as numbers, with a comment saying where they come from); only `+ − × ÷` and `Math.sqrt` (contracts/layout-determinism.md). Module comment says why no `Math.cos`/`Math.sin`. Done.
- [X] T005 [P] [US1] Create `packages/aoa-maxitor/client/src/components/diagrams/FullGraphViewer/layoutHash.ts`: `layoutHash(positions, nodeIds): Promise<string>` — SHA-256, hex, over a little-endian `Float64Array` `[x0, y0, x1, y1, …]` in the given order (`crypto.subtle.digest`); and `svgLayoutHash(svg: string): Promise<string>` for the Graphviz viewers. Done, at `packages/aoa-maxitor/client/src/lib/layoutHash.ts` instead: the Graphviz viewers use it too (spec 026's rule — `lib/` once a second viewer needs a module); plus `lib/useSvgLayoutHash.ts` for them.
- [X] T006 [US1] In `packages/aoa-maxitor/client/src/components/diagrams/FullGraphViewer/layoutSettings.ts` add `export const LAYOUT_VERSION = 2` with a comment: raise it with any change that can move a node. In `forceLayout.ts`: drop `width` and `height` from `LayoutRequest`; set `center: { x: 0, y: 0, z: 0, strength: LAYOUT_SETTINGS.centerStrength }`; give every node `x` and `y` from `initialPositions` before `execute`; keep the payload order; keep `stop()` then `tick(LAYOUT_SETTINGS.iterations)`. Done. Found: `D3ForceLayout` overrides `center.x/y` with half its viewport and takes the window's size when none is given, so the options carry `width: 0, height: 0` (research R2).
- [X] T007 [US1] In `packages/aoa-maxitor/client/src/components/diagrams/FullGraphViewer/arrangementStore.ts` add `LAYOUT_VERSION` to the fingerprint payload, so arrangements of older code are never replayed (data-model.md, "Hashes and builds"). Done.
- [X] T008 [US1] In `packages/aoa-maxitor/client/src/components/diagrams/FullGraphViewer/FullGraphViewer.tsx`: on a first open (no remembered arrangement) import `./forceLayout` lazily (`import()` in the same chunk as G6), compute the positions on the main thread, store them, and draw through `PrecomputedLayout` exactly as a repeat open does; stop passing `g6LayoutOptions` to G6; after the first draw set `data-layout-hash` on the diagram element to `layoutHash(positions, payload order)`, and remove it while a new layout runs. Remove `g6LayoutOptions` from `layoutSettings.ts` if nothing else uses it. Done, and a #245 defect fixed on the way: `buildGraph` let a literal `layout: { type: "d3-force" }` key override the given option, so G6 always laid out itself and `PrecomputedLayout` never ran (research R2). The literal block is removed; the hash is taken over the drawn positions (`graph.getElementPosition`). The layout runs in its own task before G6 builds the graph; an attempt to run it inside G6's pass measured faster only because of that defect.
- [X] T009 [P] [US1] In `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx`, `packages/aoa-maxitor/client/src/components/diagrams/UseCaseDiagramViewer/UseCaseDiagramViewer.tsx` and `packages/aoa-maxitor/client/src/components/diagrams/LifecycleFsmViewer/LifecycleFsmViewer.tsx`: after `gv.layout(dot, "svg", engine)` set `data-layout-hash` on the diagram element to `svgLayoutHash` of the returned SVG string, before any post-pass; clear it while a new layout runs. Done: the full SVG hash for use case and lifecycle (their markup is Graphviz's own), Graphviz's raw output for the ERD (kept as `rawSvg`).
- [X] T010 [US1] Create `packages/aoa-maxitor/client/src/components/diagrams/FullGraphViewer/layoutDeterminism.test.ts` on `__fixtures__/full-graph-ref.json`: (a) **guard** — spy on `Math.cos`, `Math.sin`, `Math.pow`, `Math.random` for the duration of `computeForceLayout`, each with zero calls; (b) the request type has no width or height, and the hash is equal with `window.innerWidth`/`innerHeight` set to 375×812 and 1600×900; (c) **golden** — the hash equals a constant written in the test; (d) **spiral** — `initialPositions` gives finite, distinct positions equal to a reference table for the first 16 nodes. Update `forceLayout.test.ts` to the new request shape. Done; the guard checks `Math.pow` by effect (each result moved one ulp, hash unchanged) because `d3-force-3d` calls it on every step with exact powers of two (research R2). `forceLayout.test.ts` now compares with the library's own merge around the origin. Golden hash `a07662ef…`; client 69 passed in 11 files.
- [X] T011 [US1] Adversarial check: (a) replace the rotation in `initialPositions.ts` with `Math.cos`/`Math.sin` → only test (a) fails; (b) set the centre back to `width / 2` with a width input → only test (b) fails; (c) remove the starting positions so `d3-force-3d` places nodes itself → test (a) fails (its spiral calls `cos`/`sin`), which also proves the wrapper passes `x`/`y` through (research R2); (d) change `linkDistance` → only the golden hash fails. Restore each; record here. If (c) does **not** fail, stop: the wrapper drops `x`/`y`, and the fallback of plan.md "Risks" applies. Done. (a) `cos`/`sin` in the spiral → (a) cos/sin, (c) golden and (d) spiral fail; (b) no fixed size → (b) window, (c) golden and the library-merge test fail; (c) no starting positions → (a) cos/sin, (c) golden and the library-merge test fail — the wrapper does pass `x`/`y`; (d) `linkDistance` 73 → (c) golden and the library-merge test fail; (e) `Math.pow(0.5 + i, 0.5)` in the spiral → only the `pow` guard fails. The golden hash fails with every break that moves a node, by design. Restored; 15 passed.
- [X] T012 [US1] Re-record the #245 canvas reference on purpose (the picture changes once, plan.md "Risks"): run `node scripts/measure-full-graph.ts --canvas specs/026-full-graph-fast-open/data/canvas-main.png` as in that spec's quickstart, and say in the commit message that the full graph's starting spiral and centre changed. Done: `specs/026-full-graph-fast-open/data/canvas-main.png` re-recorded from Maxitor's own layout; a second run compares identical. Measured (cpu1x, median of 3): first open first pixel 779 ms (#245: 775), longest task 353 ms (592); repeat open first pixel 397 ms (738). Hash `a07662ef…` in Chromium at 1024×768 and 375×812, first and repeat open; ERD hash equal at both sizes.
- [X] T013 [US1] Prepare commit 2: `feat(maxitor): lay the full graph out the same way on every engine and screen (#271)`. Tick issue phase 1. Committed as `a56e6f2d`; issue phase 1 ticked.

---

## Phase 3: The cross-engine step (commit 3) · US1

**Goal**: the check run proves the same layout in Chromium, Firefox and WebKit at phone and desktop size (FR-006).

**Independent Test**: `node scripts/check-layout-determinism.ts` exits 0 and prints one hash per page and layout mode.

- [X] T014 [US1] Create `packages/aoa-maxitor/client/scripts/check-layout-determinism.ts` exactly to contracts/layout-determinism.md: serve `dist/` and a stub API answering from `packages/aoa-maxitor/tests/fixtures/ref-graph-2026-10-26.json.gz` (reuse the serving approach of `scripts/measure-full-graph.ts`); for each engine × viewport (375×812, 1600×900) × page (full graph, every domain's ERD and use case, every lifecycle) × layout mode, wait for `data-layout-hash` and record it; print one line per page and mode; exit 1 on any difference, naming engine and size. Module comment: what it proves and that the check run runs it. Done: Maxitor itself (uvicorn) behind a Node server that serves `dist/` and the fixture, so no stub answers; pages come from the left panel's answer; use-case pages are walked a second time with Boundary off (Neato and FDP appear only then); mode buttons are clicked through the DOM because on a phone the open left panel covers them. Found on the way and fixed: Graphviz FDP reads state earlier layouts leave in the WebAssembly instance (five paths to the same ERD in FDP gave five hashes); `loadGraphvizWasmFor(engine)` in `client/src/lib/prefetch/erdGraphviz.ts` gives FDP a fresh instance, used by the ERD and use-case viewers (research R3).
- [X] T015 [US1] Add the step to `scripts/run_checks_with_log.sh` right after "Maxitor client: unit tests": `run_and_log "(cd packages/aoa-maxitor/client && npx playwright install chromium firefox webkit && node scripts/check-layout-determinism.ts)" "Maxitor client: the same layout in three engines"`. Done.
- [X] T016 [US1] Run the step; record the elapsed time and the number of pages × modes checked here. Adversarial check: make the full graph's centre depend on `window.innerWidth` in `forceLayout.ts` → the script fails naming the 375 and 1600 sizes and the vitest guard fails too; make one Graphviz viewer append a timestamp to its DOT → only that viewer's lines fail. Restore each; record here. Done: **56 page-modes × 3 engines × 2 sizes, all equal**, 336 layouts in 28 s; the whole step with the cached `npx playwright install` takes 24 s (the install alone 0.6 s). Breaks (Chromium): the full graph's centre from `window.innerWidth` → only `full graph | default` differs (375 vs 1600) and three vitest tests fail; a timestamp in the lifecycle DOT → exactly the six lifecycle lines differ, vitest untouched; before the FDP fix the five FDP lines differed. Restored; green.
- [X] T017 [US1] Prepare commit 3: `test(maxitor): prove the same layout in three browser engines in the check run (#271)`. Tick issue phase 2. Committed as `2f4511ab`; issue phase 2 ticked.

---

## Phase 4: Conditional answers in the adapter (commit 4) · US7

**Goal**: every adapter `GET` answer carries an `ETag`; a matching `If-None-Match` gets `304` (FR-070, contracts/http.md).

**Independent Test**: `uv run pytest packages/aoa-fastapi-adapter/tests/test_conditional_get.py -q` passes.

- [ ] T018 [P] [US7] Create `packages/aoa-fastapi-adapter/tests/test_conditional_get.py`: on an adapter app with one `GET` action: (1) a 200 carries `ETag: "<32 hex>"`; (2) the same request with that `If-None-Match` → `304`, empty body, same `ETag`; (3) `If-None-Match: *` and a list containing the tag → `304`; (4) a different tag → 200 with the body; (5) a `POST` and a 4xx carry no `ETag`; (6) the tag is equal across two app instances built from the same action and data (a restart). Confirm (1)–(4) and (6) fail before T019.
- [ ] T019 [US7] Create `packages/aoa-fastapi-adapter/src/aoa/fastapi/conditional_get.py`: a pure ASGI middleware — for `GET` with status 200 buffer the body, set `ETag` to the first 32 hex of its SHA-256, answer `304` with no body on a matching `If-None-Match`; pass everything else untouched. Install it in `FastApiAdapter.build()` in `packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py`, inside the error middleware, and add it to `build()`'s docstring list.
- [ ] T020 [US7] Run the whole adapter suite and `uv run pytest packages/aoa-maxitor/tests -q` (Maxitor's diagram routes now carry `ETag`; nothing else changes). Adversarial check: (a) compare the tag case-sensitively against a lower-cased header → only (2)–(3) fail; (b) hash the headers too → only (6) fails. Restore; record here.
- [ ] T021 [US7] Prepare commit 4: `feat(fastapi): answer conditional GET requests with ETag and 304 (#271)`. Tick issue phase 3.

---

## Phase 5: WebSocket routes in the adapter (commit 5) · US2

**Goal**: a WebSocket route maps each message to an action, relays volatile messages through a resource without an action, and enforces size and rate limits (FR-066, FR-068, FR-015; contracts/websocket-adapter.md).

**Independent Test**: `uv run pytest packages/aoa-fastapi-adapter/tests/test_websocket_route.py -q` passes.

- [X] T022 [P] [US2] Create `packages/aoa-fastapi-adapter/src/aoa/fastapi/socket_channel.py`: `SocketChannel(BaseController)` with `id`, `send(event)` (ordered queue, bounded at 256; when full close `4008` `client too slow`), `send_volatile(kind, event)` (one slot per kind, the newest wins), `close(code, reason)`, `closed`; one writer task per channel drains volatile slots and the ordered queue. Done; `SocketChannel` carries `@meta` with a small `TransportDomain`, so actions can declare it with `@connection` and the graph accepts it.
- [X] T023 [P] [US2] Create `packages/aoa-fastapi-adapter/src/aoa/fastapi/websocket_route.py`: `FastApiWebSocketRouteRecord` (path, `on_open`, `messages`, `on_close`, `relay`, `relay_key`, `connections`, `max_message_bytes` = 4096, `max_messages_per_second` = 40, tags, description) and `ConnectionRefusalError(code, reason)`; the connection loop of the contract: accept, create `SocketChannel`, run `on_open` with path and query params plus `origin` and connections `{**connections, "socket": channel}`, then per frame: size → `4413` `message too large`, rate over any one-second window → `4429` `too many messages`, `type` in `relay` → `connections[relay_key].relay(channel, message)` with no action, `type` in `messages` → validate and run that action (one at a time, arrival order), anything else → `{"type": "error", "reason": …}`; `ConnectionRefusalError` from `on_open` closes with its code, from a message action sends `refused`; on any end run `on_close`; an unexpected error closes `1011` `internal error`. Done, with two decisions written into the contract: the connection's values (path, query, `origin`) fill the params fields of the same name and a message may not set them (no speaking for another room); `on_close` runs only after `on_open` succeeded. The adapter also closes `4401` without an auth context and `4422` on open params that do not validate. The exception is `ConnectionRefusalError` (ruff N818 wants the suffix and `ConnectionRefusedError` is a Python built-in); relay targets implement the `RelayTarget` protocol.
- [X] T024 [US2] In `packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py` add `websocket(path, *, on_open, messages, on_close=None, relay=frozenset(), relay_key=None, connections={}, max_message_bytes=4096, max_messages_per_second=40, tags=(), description="")` returning `self`, and register WebSocket records in `build()` with `app.add_api_websocket_route`. Export `ConnectionRefusalError` and `SocketChannel` from `packages/aoa-fastapi-adapter/src/aoa/fastapi/__init__.py`. Done; `build()` passes each action exactly the connection keys it declares (the machine refuses extra or missing keys) and fails at start-up when a route cannot provide one.
- [X] T025 [US2] Create `packages/aoa-fastapi-adapter/tests/test_websocket_route.py` with tiny test actions and a stub relay resource, through Starlette's `TestClient.websocket_connect`: (1) `on_open` runs with path, query and `origin` params; (2) a mapped message runs its action, which replies via `socket.send`; (3) a relayed type reaches the stub's `relay` and **no action runs** (assert on the machine's run count); (4) 4 097 bytes → close `4413`; (5) 41 messages in one second → close `4429`; (6) `ConnectionRefusalError(4409, "room full")` from `on_open` → close `4409`; from a message action → a `refused` frame and the socket stays open; (7) an unknown type → an `error` frame; (8) `on_close` runs on a client disconnect; (9) ten volatile events sent to a paused reader arrive as the newest one; (10) 257 durable events to a paused reader close `4008`. Done: 13 tests on real actions and a real machine (no mocked `run`), plus `SocketChannel` against a client that never reads; the size limit is tested at 4 096 (accepted) and 4 100 bytes (closed). Adapter suite 174 passed; Maxitor 237 passed, 1 skipped; ruff, mypy clean, pylint 10.00, radon no C.
- [X] T026 [US2] Adversarial check: (a) run an action for relayed types too → only (3) fails; (b) off-by-one the size limit (`>` → `>=`) → only (4) fails; (c) make `send_volatile` append instead of replace → only (9) fails. Restore each; record here. Done: (a) an action for relayed types too → only `test_relayed_type_runs_no_action` fails; (b) `>=` in the size limit → only `test_message_at_the_size_limit_is_accepted`; (c) volatile appended to the ordered queue → only `test_volatile_keeps_only_the_newest`. Restored; 174 passed.
- [ ] T027 [US2] Prepare commit 5: `feat(fastapi): WebSocket routes that run an action per message (#271)`. No issue box of its own (issue phase 6 is ticked after commit 8).

---

## Phase 6: Graphs kept until the limit, as a resource (commit 6) · US8

**Goal**: a held graph stays until `MAXITOR_MAX_GRAPHS` is reached; new code reaches the store only through `GraphStoreController`, and `graph-json` is downloaded only through `GraphSourceGateway` (FR-080, FR-081; research R1, R7).

**Independent Test**: `uv run pytest packages/aoa-maxitor/tests/test_api_graph_store.py packages/aoa-maxitor/tests/test_graph_store_controller.py -q` passes.

- [ ] T028 [US8] In `packages/aoa-maxitor/src/aoa/maxitor/api/graph_store.py`: remove `idle_seconds` and the idle part of `sweep` (keep the failure memory); keep least-recently-read eviction beyond `max_graphs`; add `content_sha256`, `etag`, `last_modified`, `fingerprint`, `last_checked`, `checking` to `GraphEntry` (data-model.md "Held graph"); add `replace(source, build)` that builds a new entry under a build slot and swaps it in **only on success**, leaving reads in flight on their entry. Update the module header and AI-CORE `INVARIANTS`.
- [ ] T029 [US8] In `packages/aoa-maxitor/src/aoa/maxitor/api/app.py` remove `MAXITOR_GRAPH_IDLE_SECONDS`. Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/graph_source_gateway.py`: `GraphSourceGateway(BaseGateway)` owning one `httpx.AsyncClient`, `fetch(url)` → `Document(body, etag, last_modified, sha256)` | `Unreachable(reason)`, timeout 15 s, never raising for network or HTTP errors. Make `packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/load_aoa_service_action.py` download through it (`@connection(GraphSourceGateway, key="GraphSource")`) instead of `httpx` in its aspect, keeping its error wording, and return the body's SHA-256 and the `ETag` / `Last-Modified` so `build_graph_entry` stores them. This takes #278's phase 3 into this feature (research R7).
- [ ] T030 [P] [US8] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/graph_store_controller.py`: `GraphStoreController(BaseController)` over the app's `GraphStore` — `entry(source)`, `acquire(source)`, `replace(source)`, `held_sources()`, `mark_checked(source, when)`, `is_checking` / `set_checking`; no decisions.
- [ ] T031 [US8] Update `packages/aoa-maxitor/tests/test_api_graph_store.py`: a graph unread for longer than an hour is still held; beyond the limit the one read longest ago leaves; `replace` with a failing build keeps the old entry; a read started before `replace` finishes on the old entry. Create `packages/aoa-maxitor/tests/test_graph_store_controller.py` for the controller's delegation. Set `MAXITOR_MAX_GRAPHS` for the stand in `deploy/stand/docker-compose.yml` with a comment: about 22 MiB per reference graph after #268.
- [ ] T032 [US8] Adversarial check in `packages/aoa-maxitor/src/aoa/maxitor/api/graph_store.py`: (a) put the idle removal back → only the "unread for an hour" test fails; (b) swap before the build finishes → only the failing-build test fails. Restore; record here.
- [ ] T033 [US8] Prepare commit 6: `feat(maxitor): keep built graphs until the store's limit and download them through a gateway (#271)`. No box yet (issue phase 4 is ticked after commit 7).

---

## Phase 7: Fresh graphs on the server (commit 7) · US7

**Goal**: Maxitor checks every source with open tabs through a gateway, rebuilds a changed one in the background and keeps the old graph on failure (FR-071 … FR-075, FR-077).

**Independent Test**: `uv run pytest packages/aoa-maxitor/tests/test_fresh_graphs.py -q` passes.

- [ ] T034 [P] [US7] In `packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/graph_source_gateway.py` (created in T029) add validators: `fetch(url, etag, last_modified)` sends `If-None-Match` / `If-Modified-Since` and returns `NotModified` on `304`, besides `Document` and `Unreachable`.
- [ ] T035 [P] [US7] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/open_tabs_registry.py`: `OpenTabsRegistry(BaseController)` — `seen(source, when)`, `has_open_tabs(source, now)` (true when seen within 75 s or the room registry reports a connection for it).
- [ ] T036 [US7] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/check_source_action.py`: `CheckSourceAction(source, force=False)` with connections `GraphStore`, `GraphSource`, `RoomRegistry` (optional until commit 8): skip if a check of the source runs (FR-074); fetch with the held validators; `NotModified` or an equal SHA-256 → `mark_checked`, `box.info(Channel.business, "Source {source} unchanged")`; changed → `replace`, then announce `graph_changed`, `box.info(…, "Source {source} rebuilt")`; `Unreachable` or a failed build → keep the graph, `box.warning(Channel.error, …)`.
- [ ] T037 [US7] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/check_due_sources_action.py`: `CheckDueSourcesAction` picks held sources with open tabs whose `last_checked` is older than 30 s (validators present) or 120 s (none), and runs `CheckSourceAction` for each through `box.run`.
- [ ] T038 [US7] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/graph_fingerprint_action.py`: `GraphFingerprintAction(source)` records `seen` in `OpenTabs`, returns `{"fingerprint": …}` from memory, and starts a background `CheckSourceAction` when the last check is older than its interval (FR-073).
- [ ] T039 [US7] In `packages/aoa-maxitor/src/aoa/maxitor/api/app.py`: create the gateway and the registries once; register `GET /graph-fingerprint` on the adapter with its connections; in the lifespan start a timer that runs `CheckDueSourcesAction` through the machine every 10 s and stops on shutdown (the timer decides nothing — module comment says so).
- [ ] T040 [US7] Create `packages/aoa-maxitor/tests/test_fresh_graphs.py` with a local `graph-json` server whose body, `ETag` and availability the test controls: (1) unchanged with `ETag` → `304`, no rebuild; (2) without validators, equal SHA-256 → no rebuild; (3) changed body → rebuilt, new fingerprint; (4) a failing build → old graph kept, a `warning` record; (5) source down → old graph kept and still readable; (6) two `CheckSourceAction` for one source at once → one fetch; (7) a source without open tabs is not picked by `CheckDueSourcesAction`; reading its fingerprint starts a background check; (8) log records carry the source and no participant data.
- [ ] T041 [US7] Adversarial check: (a) ignore `NotModified` and rebuild → only (1) fails; (b) drop the `checking` guard → only (6) fails; (c) count tabs seen 10 minutes ago as open → only (7) fails. Restore each; record here.
- [ ] T042 [US7] Prepare commit 7: `feat(maxitor): keep held graphs up to date with their services (#271)`. Tick issue phase 4.

---

## Phase 8: Rooms on the server (commit 8) · US2, US4, US6, US9

**Goal**: rooms as actions over a registry resource, with limits, the two-minute return, the circle rule, picture checks and logging (FR-010 … FR-019, FR-054, FR-060 … FR-069, FR-090; contracts/room-actions.md, room-protocol.md).

**Independent Test**: `uv run pytest packages/aoa-maxitor/tests/test_rooms_*.py -q` passes.

- [ ] T043 [US2] Add `websockets` to `dependencies` in `packages/aoa-maxitor/pyproject.toml` (BSD-3-Clause; already in `uv.lock` transitively) and run `uv lock`; confirm `scripts/check_package_metadata.py` passes.
- [ ] T044 [P] [US2] Create `packages/aoa-maxitor/src/aoa/maxitor/model/rooms/__init__.py` and `rooms_domain.py` (`RoomsDomain`, like `core_domain.py`).
- [ ] T045 [P] [US6] Create `packages/aoa-maxitor/src/aoa/maxitor/model/rooms/follow_circle.py`: `would_close_circle(follows: Mapping[str, str | None], follower: str, target: str) -> bool` — true when `target`, following its own links, reaches `follower` (data-model.md "FollowLink"), and a test `packages/aoa-maxitor/tests/test_rooms_follow_circle.py` for direct, indirect (A→B, V→A: B may follow neither) and self cases.
- [ ] T046 [US2] Create `packages/aoa-maxitor/src/aoa/maxitor/model/rooms/resources/room_registry.py`: `RoomRegistry(BaseController)` holding rooms per data-model.md — Room (`id` "128 random bits, `secrets.token_urlsafe(16)`", `source`, `created_by`, `participants` "at most 20", `page_settings`, `reported_hashes`, `empty_since`, `lock`), Participant (`id`, `name` "1–40 characters after trimming", `colour` "the first free index of the room's palette; unique in the room; freed on leave", `tabs`, `active_tab`, `follows` "at most one", `return_until`), Tab; atomic helpers under the room lock; `broadcast(room, event, except_tab=None)`; `relay(channel, message)` sending `pointer` / `viewport` only to tabs on the same page via `send_volatile`; timers that run `EndRoomAction` and `ExpireParticipantAction` through the machine. No limits or rules inside.
- [ ] T047 [US2] Create the room actions in `packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/`, one module each, per contracts/room-actions.md: `create_room_action.py` (name 1–40 after trim, rooms < 100, `422` / `503 Retry-After: 30`), `join_room_action.py` (`origin` is Maxitor's own address; room exists; participants < 20 unless returning; name valid; `fallback_page` when the page does not exist for the room's source: the creator's active page, else the most recently active participant's; refusals `ConnectionRefusalError` 4403 / 4404 / 4409 / 4422; sends `welcome`, broadcasts `joined` unless returning), `leave_room_action.py` (clean leave vs lost connection opens the two-minute window; stops everyone who followed the leaver), `expire_participant_action.py`, `end_room_action.py`, `rename_participant_action.py`, `set_page_setting_action.py` (known setting of that page and a value exactly as data-model.md "PageSettings" lists it; "set to", last wins), `follow_action.py` (`would_close_circle` under the room lock; `follow_refused`), `stop_following_action.py`. Each logs per FR-067 with ids only (FR-069).
- [ ] T048 [P] [US9] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/static_bundle_resource.py` (`StaticBundleResource(BaseStorage)` reading `build.json` from the installed static folder) and `packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/app_info_action.py` (`AppInfoAction` → `version` from `importlib.metadata.version("aoa-maxitor")`, `build` from the resource). In `packages/aoa-maxitor/client/vite.config.ts` write `build.json` (`{"build": <first 12 hex of SHA-256 of the built index.html>}`) next to the bundle and define `__MAXITOR_BUILD__` with the same value.
- [ ] T049 [US9] Create `packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/report_page_action.py`: updates the tab's page, activity and visibility; compares `build` with `StaticBundle`, `fingerprint` with the held graph, and `layout_hash` with the room's first hash for that page and settings digest; answers `check` (`build`: ok/reload, `fingerprint`: ok/reread, `layout`: ok/off) and broadcasts `presence`.
- [ ] T050 [US2] Create `packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/reload_source_for_room_action.py`: runs `CheckSourceAction(force=True)` through `box.run` for the room's source (FR-065). Give `CheckSourceAction` its `RoomRegistry` connection so `graph_changed` reaches every room of the source.
- [ ] T051 [US9] Add `fingerprint` (the held entry's `content_sha256`, data-model.md "Held graph") to the sidebar answer: `sidebar_payload` in `packages/aoa-maxitor/src/aoa/maxitor/api/routes/sidebar.py` writes the bound entry's value and nothing else changes in the route (#278 moves it later). The client keeps it as the fingerprint of the graph it drew. Test in `packages/aoa-maxitor/tests/test_rooms_page_checks.py`: the sidebar's fingerprint equals `graph-fingerprint`'s.
- [ ] T052 [US2] Wire in `packages/aoa-maxitor/src/aoa/maxitor/api/app.py`: `POST /rooms` → `CreateRoomAction`; `.websocket("/rooms/{room_id}/live", on_open=JoinRoomAction, messages={"page": ReportPageAction, "activity": ReportPageAction, "setting": SetPageSettingAction, "rename": RenameParticipantAction, "follow": FollowAction, "stop_following": StopFollowingAction, "leave": LeaveRoomAction, "reload": ReloadSourceForRoomAction}, on_close=LeaveRoomAction, relay={"pointer", "viewport"}, relay_key=ROOM_REGISTRY_KEY, connections=…)`; a second `FastApiAdapter` app mounted at `/api/meta` with `GET /app-info` → `AppInfoAction` (research R8).
- [ ] T053 [US2] Create `packages/aoa-maxitor/tests/test_rooms_server.py` through `TestClient` with several connections: (1) create and join; `welcome` lists participants, settings and `server_build`; (2) colours unique and freed on leave; (3) two tabs of one participant are one participant, the latest active tab's page is shown; (4) the 21st join → close `4409`; the 101st room → `503`; (5) a name of spaces or 41 characters → `422` / `4422`; (6) a lost connection returning within two minutes → no `left`/`joined`; after two minutes → `left` (clock injected); (7) the empty room ends after two minutes; its link then closes `4404`; (8) a foreign `Origin` → `4403`; (9) `setting` reaches everyone and a later joiner; two crossing settings end in the last one; (10) crossing `follow` requests between two participants → exactly one succeeds; (11) `pointer` reaches only tabs on the same page and runs no action; (12) a link page missing for the room's source → `fallback_page`; (13) log records carry ids and never a name (assert on a captured logger).
- [ ] T054 [US9] Create `packages/aoa-maxitor/tests/test_rooms_page_checks.py`: a report with another build → `check.build = reload`; another fingerprint → `reread`; a different layout hash with equal build and graph → `layout = off`; equal values → all `ok`. And `packages/aoa-maxitor/tests/test_app_info.py` for `/api/meta/app-info`.
- [ ] T055 [US2] Adversarial check: (a) skip the participant limit for returning participants too → only (4) fails; (b) check the circle outside the lock → (10) fails under the crossing test; (c) log the name → only (13) fails; (d) relay `pointer` to every tab → only (11) fails. Restore each; record here.
- [ ] T056 [US2] Record in this file (not in the documentation yet) the nginx lines the stand needs for `/api/v1/rooms/` — `proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";` — so T103 can document them; the maintainer applies them on the host after commit 8.
- [ ] T057 [US2] Prepare commit 8: `feat(maxitor): rooms on the server, as actions over a registry (#271)`. Tick issue phase 6.

---

## Phase 9: Joining and the top row (commit 9) · US2

**Goal**: open, join, share, leave, rename and see each other in the top row, on desktop and phone (FR-019 … FR-028, FR-060 … FR-065; mockup screens 1–5, 9, 14, 18, 19).

**Independent Test**: `npm test` passes the room client tests; quickstart §2 steps 1–2 and §4 pass by hand.

- [ ] T058 [P] [US2] Create `packages/aoa-maxitor/client/src/rooms/connection.ts`: one WebSocket per tab to `/api/v1/rooms/{id}/live` with `participant` (from `localStorage` `maxitor.room.<id>.participant`), `tab` (`sessionStorage` `maxitor.tab`), `name`, `page`; reconnect with growing pauses (1, 2, 4, 8, 15 s cap); exposes state `connecting | open | reconnecting | closed(code, reason)`; turns close codes 4403 / 4404 / 4409 / 4422 / 4413 / 4429 / 4008 into the sentences of contracts/room-protocol.md.
- [ ] T059 [P] [US2] Create `packages/aoa-maxitor/client/src/rooms/roomStore.ts`: a React store of the room (participants, colours, presence, page settings, follow links, `you`) fed by `welcome` / `joined` / `left` / `presence` / `renamed` / `setting` / `follows` / `graph_changed`; and `packages/aoa-maxitor/client/src/rooms/initials.ts` (first letters of the first two words, else the first two letters) with `initials.test.ts`.
- [ ] T060 [US2] In `packages/aoa-maxitor/client/src/lib/urlState.ts` add the `room` parameter (read, write, remove) and a `replace` flag for navigation; keep every existing parameter as it is.
- [ ] T061 [US2] Create `packages/aoa-maxitor/client/src/rooms/RoomBar/` (`RoomBar.tsx`, `index.ts`, `README.md`): outside a room **Open room**; inside, the circles, **Copy link**, **Leave room**, **Hide pointers**; height 38 px on desktop, matching the left panel's header row, on the workspace surface, no shadow, icons 14 px; on a phone the circles and one ⋮ menu with **Copy room link**, **Leave room**, **Hide pointers** in words. Mount it in `packages/aoa-maxitor/client/src/components/layout/MainLayout/MainLayout.tsx` (desktop row; the existing 44 px bar on a phone).
- [ ] T062 [P] [US2] Create `packages/aoa-maxitor/client/src/rooms/Circles/` (`Circles.tsx`, `index.ts`, `README.md`): a circle per participant in their colour with initials in a contrasting colour, yours first and ringed, more than 5 on desktop or 3 on a phone collapse into **+N** opening a list; pale when the participant's active tab is hidden; a counter on your own circle when someone follows you.
- [ ] T063 [P] [US2] Create `packages/aoa-maxitor/client/src/rooms/NameDialog/` and `packages/aoa-maxitor/client/src/rooms/InviteCard/` (each `*.tsx`, `index.ts`, `README.md`) in the style of FR-024 and mockup screens 1–4: the name dialog (1–40 after trim, the last name prefilled from `maxitor.name`, the notice *Everyone with the link sees your name and your pointer.*), the invite card with the link, **Copy link** copying the current address with `room` (`navigator.share` on a phone where present; a selected field when the clipboard is unavailable; *Link copied*).
- [ ] T064 [US2] Create `packages/aoa-maxitor/client/src/rooms/ParticipantCard/` (`ParticipantCard.tsx`, `index.ts`, `README.md`): full name, page, *following you* (or through whom), **Go to**, **Follow** / **Follow <name> instead** (disabled with its reason when it would close a circle), and on your own card **Change name**; opens on hover and on a long press.
- [ ] T065 [US2] Notices and edge flows: *Reconnecting…* in the row while reconnecting; *Boris joined* / *Anna left* fading after a few seconds, nothing for a return within two minutes; *This room has ended* with **Open room**; *This room is full (20 people)*; in `packages/aoa-maxitor/client/src/components/navigation/LeftSidebar/LeftSidebar.tsx` *Load a different service* asks *Leave the room and open another service?* inside a room; **Reload** inside a room sends `reload` instead of `POST /api/load`. **Leave room** keeps the page, settings and layout mode and removes `room` from the address.
- [ ] T066 [US2] Keyboard and screen readers: every circle, the +N list and every row button reachable with Tab and opened with Enter; each circle labelled with the full name and page; Esc closes a card. Create `packages/aoa-maxitor/client/src/rooms/rooms.test.ts` for the store's reduction of server events, the close-code sentences, the copied address (current page + `room`) and initials.
- [ ] T067 [US2] Adversarial check: (a) copy the creation page instead of the current address → only the copied-address test fails; (b) show `joined` for a return → only that store test fails. Restore; record here. Check the screens against mockup screens 1–5, 9, 14, 18, 19 at 1600×900 and 375×812.
- [ ] T068 [US2] Prepare commit 9: `feat(maxitor): open, join and share a room from the top row (#271)`. Tick issue phase 7.

---

## Phase 10: Shared page settings (commit 10) · US4

**Goal**: inside a room every filter and layout mode is the room's, per page; outside a room nothing changes (FR-030 … FR-033).

**Independent Test**: `npm test` passes `pageSettings.test.ts`; quickstart §2 step 4 passes by hand.

- [ ] T069 [US4] Create `packages/aoa-maxitor/client/src/lib/pageSettings.ts`: `usePageSetting<T>(pageKey, name, defaultValue)` — outside a room reads and writes the local map it replaces; inside a room reads the room's value and sends `{"type": "setting", "page", "name", "value"}` ("set to", never toggle); page keys canonical per data-model.md "PageKey".
- [ ] T070 [US4] Move every page setting behind `usePageSetting`: in `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx` `layout`, `domains`, `entities`, `disabled_kinds`; in `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/ErdViewer.tsx` `one_hop`; in `packages/aoa-maxitor/client/src/components/diagrams/UseCaseDiagramViewer/UseCaseDiagramViewer.tsx` `layout`, `rankdir`, `domains`, `boundary`; in `packages/aoa-maxitor/client/src/components/diagrams/LifecycleFsmViewer/LifecycleFsmViewer.tsx` `rankdir`. Remove the module-level maps they replace. Zoom, scroll, hover, highlights and collapsed panels stay personal.
- [ ] T071 [US4] Create `packages/aoa-maxitor/client/src/lib/pageSettings.test.ts`: outside a room a value persists per page as before; inside a room a change sends one `setting` message and applies the room's echo; two pages keep separate values; a room value arriving for another page does not touch this one.
- [ ] T072 [US4] Adversarial check in `packages/aoa-maxitor/client/src/lib/pageSettings.ts`: send a toggle instead of the value → the test of the sent message fails; key settings without the page → the two-pages test fails. Restore; record here.
- [ ] T073 [US4] Prepare commit 10: `feat(maxitor): filters and layout modes shared by everyone in a room (#271)`. Tick issue phase 8.

---

## Phase 11: Pointers and out-of-date tabs (commit 11) · US3, US9

**Goal**: everyone sees everyone's pointer on the same spot of the diagram at any zoom; a stale tab reloads itself; a mismatched layout turns pointers off (FR-040 … FR-045, FR-090 … FR-093; mockup screens 6–8, 17).

**Independent Test**: `npm test` passes `coordinates.test.ts` and `pageCheck.test.ts`; quickstart §2 step 3 and §6 pass by hand; SC-003 measured within 2 px.

- [ ] T074 [P] [US3] In `packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/hooks/useSvgPanZoom.ts` add an `onTransform` callback and `centreOn(point)` keeping the zoom; create `packages/aoa-maxitor/client/src/rooms/coordinates.ts` with `clientToDiagram` / `diagramToClient` for an SVG (`getScreenCTM()` and its inverse) and for G6 (`getCanvasByClient` / `getClientByCanvas`), and `coordinates.test.ts` for the SVG maps with a stubbed CTM.
- [ ] T075 [US3] Create `packages/aoa-maxitor/client/src/rooms/PointerLayer/` (`PointerLayer.tsx`, `index.ts`, `README.md`): one overlay per viewer; draws mouse pointers as an arrow with a name tag in the participant's colour and touches as a ring fading after about a second; re-projects on every G6 `aftertransform` and every `onTransform`; pointers outside the view as edge arrows with initials, a click centring on that pointer at the same zoom; a pointer fades after 10 s without movement; all pointers hidden while reconnecting and while **Hide pointers** is on (`maxitor.hidePointers`).
- [ ] T076 [US3] Send pointers and viewports: Pointer Events on each viewer's diagram element → `{"type": "pointer", "kind", "x", "y"}` in diagram coordinates at most 20 times a second and only when moved; `{"type": "viewport", "cx", "cy", "w", "h"}` on every pan and zoom, at most 10 times a second (a tab stays under 30 messages a second, FR-043); nothing from a hidden tab (`visibilitychange` also sends `activity`). Wire it in the four viewers.
- [ ] T077 [US9] Create `packages/aoa-maxitor/client/src/rooms/pageCheck.ts`: after each draw send `page` with `build` (`__MAXITOR_BUILD__`), the fingerprint the sidebar answer carried (T051), `data-layout-hash` and the settings digest; on `check.build = reload` show *Maxitor was updated — reloading…*, store zoom and centre in `sessionStorage` `maxitor.view.restore` and reload unless `maxitor.reload.at` is under 5 minutes old; on `reread` re-read the graph in place; on `layout = off` turn pointers off on that page in both directions and show *Pointers are off on this page: your diagram is laid out differently from the room's.* Restore zoom and centre after a self-reload. Create `pageCheck.test.ts` for the three outcomes and the five-minute guard.
- [ ] T078 [US3] Measure SC-003 by hand with `packages/aoa-maxitor/client/src/rooms/PointerLayer/PointerLayer.tsx` in place: two browsers in one room, one at 375×812; place a pointer on a node centre and read its screen offset in the other before and after zooming each; record the largest offset here (must be ≤ 2 px). T079 then automates it in the check run.
- [ ] T079 [US3] In `packages/aoa-maxitor/client/scripts/check-layout-determinism.ts` replace the `skip` line with the pointer case of SC-003: two pages in one room on the served fixture (375×812 and 1600×900), a pointer placed on a node's centre in one, its drawn position in the other within 2 px, before and after zooming either, in all three engines.
- [ ] T080 [US3] Adversarial check: (a) send client pixels instead of diagram coordinates → `coordinates.test.ts` round-trip fails and the hand check shows the drift; (b) drop the five-minute guard → only that `pageCheck` test fails. Restore; record here.
- [ ] T081 [US3] Create `packages/aoa-maxitor/client/src/rooms/throttle.test.ts`: moving the pointer and panning at once for 3 s sends at most 30 messages in any one second (FR-043). Break: raise the viewport rate to 20 a second → the test fails; restore; record here.
- [ ] T082 [US3] Prepare commit 11: `feat(maxitor): see everyone's pointer in a room, at any zoom (#271)`. Tick issue phase 9.

---

## Phase 12: Pages redraw on a new graph (commit 12) · US7

**Goal**: a changed model reaches every open tab of its source and redraws it in place (FR-076; mockup screen 16).

**Independent Test**: `npm test` passes `freshGraph.test.ts`; quickstart §5 passes by hand.

- [ ] T083 [US7] Create `packages/aoa-maxitor/client/src/api/graphFingerprint.ts` and `packages/aoa-maxitor/client/src/lib/freshGraph.ts`: outside a room poll `GET /api/v1/graph-fingerprint?source=` every 30 s while the tab is visible; inside a room react to `graph_changed`; on a new fingerprint re-read the sidebar and the current diagram, keep page, settings, layout mode, zoom and centre, drop settings that name things no longer in the model, show *The model was updated* for a few seconds.
- [ ] T084 [US7] Create `packages/aoa-maxitor/client/src/lib/freshGraph.test.ts`: an equal fingerprint does nothing; a new one triggers one re-read and keeps the view; a removed domain leaves the enabled set; polling stops while hidden.
- [ ] T085 [US7] Adversarial check in `packages/aoa-maxitor/client/src/lib/freshGraph.ts`: keep settings that name removed domains → only that test fails; restore; record here.
- [ ] T086 [US7] Prepare commit 12: `feat(maxitor): open pages redraw by themselves when the model changes (#271)`. Tick issue phase 5.

---

## Phase 13: Going to someone (commit 13) · US5

**Goal**: a click on a circle, **Go to** or an edge arrow opens that participant's active page centred on their pointer or screen, at your zoom (FR-050).

**Independent Test**: quickstart §3 step 1 passes by hand; `goTo.test.ts` passes.

- [ ] T087 [US5] Create `packages/aoa-maxitor/client/src/rooms/goTo.ts`: navigate to the participant's active page (with `urlState`), then `centreOn` their last pointer, or their viewport centre when they have none, without changing the zoom; wire it to circles, **Go to** and edge arrows. Create `goTo.test.ts` for the choice pointer vs viewport centre and the unchanged zoom.
- [ ] T088 [US5] Adversarial check: apply the participant's `w`/`h` as a zoom → the unchanged-zoom test fails; restore; record here.
- [ ] T089 [US5] Prepare commit 13: `feat(maxitor): go to anyone in the room with one click (#271)`. Tick issue phase 10.

---

## Phase 14: Following (commit 14) · US6

**Goal**: follow, switch, stop; never a circle; your zoom stays yours; history is not flooded (FR-051 … FR-057; mockup screens 11–13).

**Independent Test**: quickstart §3 steps 2–3 pass by hand; `follow.test.ts` passes.

- [ ] T090 [US6] Create `packages/aoa-maxitor/client/src/rooms/follow.ts`: **Follow** sends `follow`; while following, apply the followed person's page (navigation with `replace: true`) and viewport centre (never their `w`/`h`); stop on your own pan, your own navigation, **Stop**, Esc, or their leaving; **Follow <name> instead** switches in one step; zooming does not stop following. Mirror `would_close_circle` in `packages/aoa-maxitor/client/src/rooms/followCircle.ts` to disable **Follow** with its reason in the card; the server stays the authority (`follow_refused` updates the card).
- [ ] T091 [US6] Create `packages/aoa-maxitor/client/src/rooms/FollowFrame/` (`FollowFrame.tsx`, `index.ts`, `README.md`): a frame in the followed person's colour around the workspace with "Following <name> · Stop" (above the zoom bar on a phone).
- [ ] T092 [US6] Create `packages/aoa-maxitor/client/src/rooms/follow.test.ts` and `followCircle.test.ts`: following applies page and centre and keeps zoom; zoom does not stop it, pan does; Follow instead switches; navigation while following uses `replace`; the circle rule matches the server's cases (direct, indirect, self).
- [ ] T093 [US6] Adversarial check in `packages/aoa-maxitor/client/src/rooms/follow.ts`: (a) push instead of replace → only the history test fails; (b) stop following on zoom → only that test fails. Restore; record here.
- [ ] T094 [US6] Prepare commit 14: `feat(maxitor): follow someone through the room at your own zoom (#271)`. Tick issue phase 11.

---

## Phase 15: ERD table style (commit 15) · US10

**Goal**: ERD tables as in mockup screen 21 (FR-110 … FR-115).

**Independent Test**: `node scripts/check-erd-table-style.ts` passes; a table matches screen 21.

- [ ] T095 [US10] In `packages/aoa-maxitor/client/src/lib/buildDotSource.ts`: header filled with the domain colour and flush with the frame, sharing its rounded top corners, entity name white, semibold, left-aligned; frame in the domain colour, white body, rounded corners; every second row tinted with the domain colour at 6 %; `PK` bold `#b45309` and `FK` bold `#475569` in their own column before the field name; field name left, type smaller and grey right-aligned; relation lines grey with a filled arrowhead, generalization dashed; proportions header 30, row 20, frame 1.4, radius 9 in diagram units.
- [ ] T096 [US10] Create `packages/aoa-maxitor/client/scripts/check-erd-table-style.ts` (pattern of `check-erd-kinds-and-lines.ts`) asserting each FR-110 … FR-115 property on the real WASM Graphviz output, and add it to `scripts/run_checks_with_log.sh` after "Maxitor client: ERD kinds, tables and lines". Adversarial check: drop the row tint → only its assertion fails; restore; record here.
- [ ] T097 [US10] Prepare commit 15: `feat(maxitor): ERD tables in the mockup's style (#271)`. Tick issue phase 12.

---

## Phase 16: Left panel footer (commit 16) · US11

**Goal**: the project link, name and version at the bottom of the left panel (FR-100 … FR-102; mockup screen 20).

**Independent Test**: the footer shows the version `GET /api/meta/app-info` returns; collapsed, only the mark with its tooltip.

- [ ] T098 [US11] Create `packages/aoa-maxitor/client/src/api/appInfo.ts` and add the footer to `packages/aoa-maxitor/client/src/components/navigation/LeftSidebar/LeftSidebar.tsx`: the GitHub mark linking to `https://github.com/bystrovmaxim/aoa/tree/main/packages/aoa-maxitor` in a new tab, then **Maxitor** and the version, centred, no divider, no copyright; collapsed — only the mark with the tooltip "Maxitor on GitHub". Update `packages/aoa-maxitor/client/src/components/navigation/LeftSidebar/README.md`.
- [ ] T099 [US11] Adversarial check: hard-code a version string → the footer no longer equals `app-info` after a version bump in a test build; restore; record here.
- [ ] T100 [US11] Prepare commit 16: `feat(maxitor): a link to the project and the running version in the left panel (#271)`. Tick issue phase 13.

---

## Phase 17: Closing check run (commit 17)

- [ ] T101 Run `bash scripts/run_checks_with_log.sh` from the repository root and fix every remark until it is green, leaving only the two accepted remarks (constitution, "Final step"); review what `ruff --fix` changed. Record the step count and time here.
- [ ] T102 Prepare commit 17 with whatever the run changed: `chore: take the check run to zero (#271)`.

---

## Phase 18: Documentation (commit 18)

- [ ] T103 Add sections to `docs/tutorials/step-26-maxitor.md` for every case this feature introduces (constitution VI.4): opening and joining a room; each refusal (ended, full, invalid name, foreign origin, size, rate, slow client); pointers and Hide pointers; shared settings; going to someone; following, switching, stopping and the refused circle; a lost connection and the two-minute return; an out-of-date tab; fresh graphs with `ETag`/`304`, with a content hash, and a source that does not answer; graphs kept until the limit; the stand's nginx lines recorded in T056, in `docs/tutorials/step-26-maxitor.md` and in the deployment part of `packages/aoa-maxitor/README.md`.
- [ ] T104 [P] Create `examples/step_26_maxitor/08_rooms.py` and `examples/step_26_maxitor/08_rooms.ipynb`: two clients joining a room through `TestClient`, a setting shared, a pointer relayed, a refused circle, a full room — executed with the repository's environment while written, the notebook's outputs as printed.
- [ ] T105 [P] Create `examples/step_26_maxitor/09_fresh_graphs.py` and `examples/step_26_maxitor/09_fresh_graphs.ipynb`: an adapter answer with `ETag`, a `304`, a changed source rebuilt, an unreachable source kept — executed while written.
- [ ] T106 Write the Russian draft beside the page, `docs/tutorials/step-26-maxitor.ru_draft.md` (not committed), and prepare commit 18: `docs(maxitor): rooms and fresh graphs, with runnable examples (#271)`.

---

## Phase 19: Changelog (commit 19)

- [ ] T107 Write one article in `docs/CHANGELOG.md` about what this work created — looking at a service together, pointers, following, graphs that stay fresh and ready — in plain words with the nuances a user needs (the link is the invitation, names are not verified, the stand's nginx must pass WebSockets), without technical detail or a per-file account (constitution VI.3).
- [ ] T108 Prepare commit 19: `docs(changelog): look at one service together (#271)`. Tick issue phase 14.

---

## Dependencies

- Commit 1 first. Commits 2 → 3 (the step needs the hashes). Commits 4, 5, 6 are independent of each other and of 2–3.
- Commit 7 needs 4 (validators) and 6 (the store resource). Commit 8 needs 5 (WebSocket routes) and 6; it gives `CheckSourceAction` its room connection.
- Client commits 9 → 10 → 11 → 13 → 14 follow 8; commit 11 also needs 2 (the layout hash); commit 12 needs 7 and 9.
- Commits 15 and 16 are independent of the rooms (16 needs `AppInfoAction` from 8).
- Commits 17 → 18 → 19 last, after everything.

**User-story order**: US1 (commits 2–3) and US8 (6) and the adapter (4–5) can start at once; US2 (8–9) → US4 (10) → US3/US9 (11) → US5 (13) → US6 (14); US7 (4, 7, 12); US10 (15) and US11 (16) at any time.

## Parallel examples

- **US1**: T003, T004, T005 together; T009 alongside T008.
- **Adapter**: T018 (tests) beside T022 and T023 (WebSocket modules) — different packages' files.
- **US7 server**: T034 and T035 together, then T036–T038.
- **US2 server**: T044, T045, T048 together, then T046 → T047.
- **US2 client**: T058, T059 together; T062, T063 together once T061 exists.

## Implementation strategy

- **MVP**: commits 1–3 and 5, 6, 8, 9, 11 — a room people can join from the top row, seeing each other's pointers on identical pictures. It is shippable on its own; settings, going to, following and fresh graphs add to it without changing it.
- **Then**: 10 (shared settings), 13–14 (go to, follow), 4, 7, 12 (fresh graphs), 15–16 (ERD style, footer), and the tail 17–19.
- Each commit is shown and waits for the maintainer's instruction; the issue box is ticked with its sha when it lands.
