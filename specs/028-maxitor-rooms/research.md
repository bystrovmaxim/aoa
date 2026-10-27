# Research: Maxitor Rooms

Every decision below was checked against the code on 2026-10-27, on the branch `feature/issue-271-maxitor-rooms` (main at `58c7d812`, with #245, #239 and #268 merged). Paths are relative to the repository root.

## R1 — The architectural rule this feature is built under

**Decision**: every piece of new server work is an AOA action, and everything an action touches outside itself is a resource.

- An endpoint — HTTP or WebSocket — only turns its transport into an action run. Transports are adapters; Maxitor writes no hand-written route.
- A store (the room registry, the graph store, the remembered fingerprints) and a service (an AOA service's `graph-json`) are reached only through a resource passed in `connections`.
- Decisions (is the room full, does this follow close a circle, has the source changed, which sources are due for a check) are made in aspects, so they are visible on Maxitor's own graph and logged through `box`.
- The resource kind follows the framework's own taxonomy (`packages/aoa-action-machine/src/aoa/action_machine/resources/`): an in-process engine the process creates and owns is a `BaseController`; an external service the process calls is a `BaseGateway` / `ExternalServiceResource`; an external store is a `BaseStorage`.

**Rationale**: the maintainer's most critical architectural requirement (spec FR-066 … FR-069, checklist notes). Today's Maxitor breaks it in older code (`/api/load`, `/api/sidebar`, `/api/health`, `GraphSourceMiddleware`, `httpx` inside `LoadAOAServiceAction`); fixing that is #278 and is out of scope here, but nothing new may copy it.

**Alternatives considered**: a Maxitor-local WebSocket handler that calls `machine.run` itself — rejected: it is a hand-written route with a different transport, and the next feature would copy it. A room registry read directly by the handler — rejected: a store outside a resource.

## R2 — Identical full-graph positions

**What the code does today**
- The viewer lets **G6 lay the graph out** on the first open: `FullGraphViewer.tsx` passes `g6LayoutOptions(...)` (`layoutSettings.ts`) and G6 merges `width`, `height` and the centre `width / 2, height / 2` itself. On a repeat open it replays positions from IndexedDB through `PrecomputedLayout` (`precomputedLayout.ts`), so no layout runs (spec 026, R14).
- `forceLayout.ts` (`computeForceLayout`) runs the same `D3ForceLayout` of `@antv/layout` 2.0.0 by hand and equals G6's result to 1e-9 (spec 026, R13). It is used only by its test and by an unused worker: the worker cost 350–450 ms of first pixel and saved nothing, so #245 did not wire it.
- Inside `d3-force-3d`, a node without `x`/`y` is placed on a phyllotaxis spiral with `Math.cos` / `Math.sin` (`node_modules/@antv/layout/lib/node_modules/d3-force-3d/src/simulation.js:93–94`); the default `alphaDecay` uses `Math.pow` (`simulation.js:30`) but is overridden by `LAYOUT_SETTINGS.alphaDecay`. Random numbers come from a fixed-seed `lcg()` (`simulation.js:36`).
- The arrangement fingerprint covers node ids and types, edges and `LAYOUT_SETTINGS`, but not the layout *code* (`arrangementStore.ts`).

**Decision**
1. **Maxitor computes the layout itself on every first open**, with `computeForceLayout` on the main thread, and draws the result through `PrecomputedLayout` — the path a repeat open already uses. G6's own layout is no longer used for the full graph. `forceLayout.ts` is imported lazily, in the same chunk as G6, so the page every view loads does not grow (spec 026, R2).
2. **Centre at the origin**: `center: { x: 0, y: 0, z: 0, strength }`; `width` / `height` are no longer inputs of the layout request. Fitting into the canvas stays G6's camera work.
3. **Starting positions**: a new pure module `initialPositions.ts` places node *i* on the golden-angle spiral with `r = initialRadius · sqrt(0.5 + i)` and the angle advanced by multiplying the previous unit vector by two literal constants (cos and sin of the golden angle). Only `+ − × ÷` and `Math.sqrt` are used; every node enters the layout with `x` and `y`, so `d3-force-3d` never reaches its spiral.
4. **Order**: nodes and edges enter in the order of the server's answer (`full_graph_action.py` orders them in SQL); nothing between the answer and the layout reorders.
5. **Layout version**: `LAYOUT_VERSION` (an integer in `layoutSettings.ts`) joins the fingerprint payload, so arrangements remembered by older code are never replayed.
6. **The layout hash**: SHA-256 over the positions as little-endian `Float64` pairs in payload order, hex (`client/src/lib/layoutHash.ts`, shared by all four viewers). The same function is used by the tests, the cross-engine tool and the room's check (R9).

**Rationale**: ECMAScript requires `+ − × ÷` and `Math.sqrt` to be correctly rounded IEEE-754 double operations and forbids fusing them; `cos`, `sin` and `pow` are implementation-approximated. A computation of the first kind over the same input in the same order gives the same bits in V8, JavaScriptCore and SpiderMonkey, on x86 and ARM. Every browser on iOS is WebKit, so the three engines cover phones.

**Picture change**: the starting spiral is the same pattern computed differently, so the final picture keeps its character but is not bit-identical to today's; the centre moves from the canvas middle to the origin, which the camera's fit hides. The golden hash is recorded once, on purpose, in phase 1.

**Alternatives considered**
- Keep G6's layout and only pass `center: {x: 0, y: 0}` — rejected: G6 merges its own options and the initial spiral would still use `cos`/`sin`.
- Wire the #245 worker — rejected for the same measured reason as in #245 (first pixel +350–450 ms, no freeze gain).
- Compute the layout on the server — rejected: the server is Python, the picture would change, and positions would have to be trusted from one place anyway.
- Send positions from one participant to the room — rejected: unnecessary once determinism holds, and the room must not hold graph data (FR-017).

**Verified in commit 2, not assumed**
- `D3ForceLayout` passes the given `x`/`y` through to `d3-force-3d`: the guard test has zero `Math.cos` / `Math.sin` calls, and removing the starting positions makes it fail.
- `D3ForceLayout.getCenterOptions` always overrides `center.x` / `center.y` with half its viewport, and `normalizeViewport` takes `window.innerWidth` / `innerHeight` when no size is given (`@antv/layout/lib/util/viewport.js`). A centre of `{x: 0, y: 0}` alone therefore does nothing; the options carry `width: 0, height: 0`.
- `d3-force-3d` calls `Math.pow` on every step (`collide.js:98`, `Math.pow(2, nDim)`) and once at creation (`simulation.js:30`, an overridden default). The guard checks that moving every `pow` result by one ulp leaves the hash unchanged.
- **A #245 defect found and fixed here.** `buildGraph` in `FullGraphViewer.tsx` spread the given layout option *before* a literal `layout: { type: "d3-force", … }` key, so the literal won: G6 laid the graph out itself on every open, `PrecomputedLayout` was never executed, and the remembered arrangement was stored but never replayed (drawn and stored positions of node 0: `[652, 852]` vs `[-187, 538]`). The literal block is removed; the hash is now taken over the drawn positions, so such a mismatch cannot hide again.
- The same fixture gives the same hash (`a07662ef…`) in Node (vitest) and in Chromium at 1024×768 and 375×812, on a first open and on a repeat open.

**Measured** (`measure-full-graph.ts`, cpu1x, median of 3, the frozen reference graph):

| | #245 final | Commit 2 |
|---|---|---|
| first open, first pixel | 775 ms | 779 ms |
| first open, longest task | 592 ms | 353 ms |
| repeat open, first pixel | 738 ms | 397 ms |
| repeat open, longest task | 584 ms | 250 ms |

The first open now has two tasks — Maxitor's layout (≈ 355 ms) and G6's drawing (≈ 250 ms) — instead of one; the repeat open draws without any layout, as #245 intended, and meets #245's SC-006 (< 500 ms) for the first time.

## R3 — The cross-engine tool and its place in the check run

**Decision**: `packages/aoa-maxitor/client/scripts/check-layout-determinism.ts`, run with Node like the other `scripts/check-*.ts`. It builds the client, serves it with a fixture graph, opens every page in every layout mode in Chromium, Firefox and WebKit through Playwright (already a dev dependency since #245), at 375×812 and 1600×900, reads the layout hash each page exposes on its diagram element (`data-layout-hash`, R9) and exits non-zero when any differs. A new step in `scripts/run_checks_with_log.sh`, after the client's unit tests, runs `npx playwright install chromium firefox webkit` and then the script.

**Fixture**: the frozen reference graph already used by #268 and #245 (`specs/025-graph-index-memory/data/`), copied into `packages/aoa-maxitor/tests/fixtures/` so the check does not read a spec folder.

**Found while building it (commit 3)**: Graphviz's FDP in the `@hpcc-js/wasm-graphviz` build reads state that earlier layouts leave in the WebAssembly instance. The same ERD in FDP gave `9d0d010c…` when FDP was the page's second layout and a different hash on every run when Dot and Neato ran before it — at the same size, in the same engine. In Node the same instance repeats FDP exactly, and an explicit `start=1` changes nothing, so the cause is the browser instance's history, not the seed. `loadGraphvizWasmFor(engine)` (`client/src/lib/prefetch/erdGraphviz.ts`) therefore gives FDP a freshly instantiated module; every other engine shares one. With it, five different paths to FDP give the same hash. Use-case diagrams offer Neato and FDP only with Boundary off, so the tool walks those pages a second time that way.

**Rationale**: the maintainer chose the mandatory check run (clarification 1). The hash on the element is read by any test and by the room (R9), so no production hook exists only for the tool.

**Risk**: on Linux, `playwright install --with-deps` needs system packages and root; the check run is local today (constitution, "Final step") and runs on macOS. The plan records it; if CI ever runs the script, its image installs the dependencies.

**Alternatives considered**: running the tool by hand before merge — declined by the maintainer.

## R4 — Conditional answers in the FastAPI adapter

**Decision**: `FastApiAdapter.build()` adds a small ASGI middleware to the app it builds: for a `GET` with status 200, it hashes the body (SHA-256, first 32 hex), sets `ETag: "<hash>"`, and when the request's `If-None-Match` matches, answers `304` with no body and the same `ETag`. Streaming and non-200 answers pass untouched. It is transport work, like gzip, and decides nothing about the domain.

**Rationale**: FR-070; every AOA service built on the adapter — including the demo's `graph-json` route, which is an action (`aoa-demo/.../app_fastapi_service.py`) — gets validators without its own code.

**Alternatives considered**: a `Cache-Control`/`Last-Modified` scheme — rejected: the demo builds its graph at start-up, so a content hash is the only stable validator; a restart with the same model must not look like a change.

## R5 — WebSocket routes in the FastAPI adapter

**Decision**: a generic WebSocket route type in `aoa-fastapi-adapter`, declared like the HTTP ones:

```python
adapter.websocket(
    "/rooms/{room_id}/live",
    on_open=JoinRoomAction,
    messages={"setting": SetPageSettingAction, "follow": FollowAction, ...},
    on_close=LeaveRoomAction,
    relay={"pointer", "viewport"},
    relay_key=ROOM_REGISTRY_KEY,
    connections={ROOM_REGISTRY_KEY: registry},
)
```

- On connect the adapter creates a per-connection resource, `SocketChannel` (a `BaseController` holding a bounded send function), and runs `on_open` with the query parameters as params and `{**connections, "socket": channel}`. A refusal raised by the action closes the socket with its code and reason.
- Each JSON message is validated against the mapped action's params and runs that action with the same connections. Messages are processed in arrival order per connection.
- A message whose type is in `relay` runs **no action** and is not logged (FR-068): the adapter hands it to `connections[relay_key].relay(channel, message)`. The resource owns where it goes; the adapter decides nothing.
- On disconnect the adapter runs `on_close`.
- Outbound messages are sent by resources through `SocketChannel.send`. Volatile messages (pointer, viewport) go through a one-slot outgoing queue per channel, so a slow connection gets the newest one (FR-043); durable events go through an ordered bounded queue, and a connection that cannot keep up is closed with a reason.

**Rationale**: it keeps Maxitor free of a hand-written route (R1) and gives every adapter user the same shape. Starlette already implements WebSocket; the adapter only needs a server implementation installed — `websockets` (BSD-3-Clause) is added to `aoa-maxitor` (the package that runs uvicorn), not to the adapter.

**Alternatives considered**: a separate `aoa-websocket-adapter` package — rejected: the HTTP and WebSocket routes of one app share the machine, the auth coordinator and the app object. Server-Sent Events plus POSTs — rejected: pointers at 20 a second per person need one duplex connection.

## R6 — Rooms: registry, actions, logging

**Decision**
- `RoomRegistry` — a `BaseController` resource, one per process, in `aoa/maxitor/model/rooms/resources/`. It holds rooms, participants, their channels, page settings, follow links and the two-minute return windows, and offers small atomic operations under one `asyncio.Lock` per room. It decides nothing: limits, circles and rules are checked by actions.
- Actions in `aoa/maxitor/model/rooms/actions/`, one per operation: `CreateRoomAction` (HTTP `POST /api/v1/rooms`), `JoinRoomAction` (`on_open`), `LeaveRoomAction` (`on_close` and the explicit leave), `RenameParticipantAction`, `SetPageSettingAction`, `ReportPageAction` (active page, layout hash, fingerprint, build), `FollowAction`, `StopFollowingAction`, `ReloadSourceForRoomAction` (the room side of **Reload**). Each declares its connections with `@connection`, its roles with `@check_roles(GuestRole)`, its domain `RoomsDomain`.
- Logging per FR-067: `box.info(Channel.business, …)` for created, ended, joined, left, reconnected; `box.warning(Channel.security, …)` for every refusal (limit name, foreign `Origin`, a follow that would close a circle); `box.critical(Channel.error, …)` for internal failures. Records carry the room id and participant id only (FR-069).
- The end of an empty room after two minutes and the end of a return window are timers of the registry that run `EndRoomAction` / `ExpireParticipantAction` through the machine, so the decision and its log stay in an action.
- Limits (clarification 2): 20 participants per room, 100 rooms per process, 40 messages a second per connection, 4 KB per message. Rate and size are enforced by the adapter's route options (`max_message_bytes`, `max_messages_per_second`), which close the socket with the reason; the count limits are checked by `CreateRoomAction` and `JoinRoomAction`.
- The circle rule (FR-054) is a pure function over the follow links, called by `FollowAction` while it holds the room lock, so two crossing requests cannot both pass.

**Rationale**: R1. The registry is in-process state the process owns, which is what `BaseController` is for.

**Alternatives considered**: state inside actions (class attributes) — rejected: actions are stateless by construction; a dict on `app.state` — rejected: a store outside a resource.

## R7 — Fresh graphs and graphs kept until the limit

**Decision**
- `GraphStoreController` — a `BaseController` resource over the existing `GraphStore`, which new actions use to read, replace and count held graphs. (#278 later moves the old routes onto it.)
- `GraphSourceGateway` — a `BaseGateway` resource owning `httpx`: `fetch(url, validators) -> NotModified | Document(body, etag, last_modified, sha256)`, 15 s timeout, errors as typed results. `LoadAOAServiceAction` downloads through it as well (maintainer, 2026-10-27, taking #278's phase 3 into this feature), so the first build already records the body's SHA-256 and validators.
- `CheckSourceAction(source)`: asks the gateway with the held graph's validators; on `304` or an equal SHA-256 it records the check and stops; otherwise it builds the new graph through the controller's build slots and swaps it in only on success; it logs what it did. `CheckDueSourcesAction` decides which held sources are due (with open tabs: 30 s with validators, 2 min without) and runs `CheckSourceAction` for each through `box.run`.
- A **timer** started in the app's lifespan runs `CheckDueSourcesAction` every 10 s. It is a trigger, like an adapter: it carries no decision.
- **Open tabs** are known from two places: room connections, and `GraphFingerprintAction` (`GET /api/v1/graph-fingerprint?source=…`), which a tab outside a room calls every 30 s and which records "seen" for that source in `OpenTabsRegistry` (a small `BaseController`). A source seen within 75 s has open tabs.
- A source held without open tabs is not checked on a timer; `GraphFingerprintAction` and every graph read trigger a background `CheckSourceAction` when the last check is older than the interval (FR-073).
- The idle timeout and `MAXITOR_GRAPH_IDLE_SECONDS` are removed from `GraphStore`; eviction is least recently read beyond `MAXITOR_MAX_GRAPHS` (FR-080). The stand's value is set in `deploy/stand/docker-compose.yml` from the machine's memory: 22 MiB per reference graph after #268, so 50 graphs ≈ 1.1 GiB.
- Inside a room a changed graph is announced by the registry to every channel of the source; outside a room the tab learns it from the fingerprint poll. The tab re-reads the sidebar and the current diagram and keeps the page, settings, zoom and centre (FR-076).

**Rationale**: FR-070 … FR-081; every network call goes through the gateway, every decision through an action.

**Alternatives considered**: a source-side push (webhook) — rejected: not every source is an AOA service; polling with validators costs one `304` per source per 30 s.

## R8 — The page's build and version

**Decision**: the Vite build writes `build.json` (`{"build": "<sha256 of the bundle's index.html, 12 hex>"}`) next to the bundle and defines `__MAXITOR_BUILD__` with the same value. `AppInfoAction` returns `{"version": <importlib.metadata.version("aoa-maxitor")>, "build": <from build.json>}`; it reads `build.json` through `StaticBundleResource` (a `BaseStorage` over the installed static folder). It is served by a second adapter app mounted at `/api/meta`, because every path under `/api/v1` is treated as a graph read by today's `GraphSourceMiddleware` and would demand a `source`.

**Rationale**: FR-090 (the build a tab reports) and FR-101 (the version in the footer, never written by hand) share one action.

**Alternatives considered**: the Python package version as the build id — rejected: two client builds of one version would look equal.

## R9 — Room checks of a tab's picture

**Decision**: every viewer writes the hash of what it laid out on its diagram element (`data-layout-hash`): the full graph its positions hash (R2), the Graphviz viewers SHA-256 of the SVG markup Graphviz returned for the page's DOT (before the viewer's own post-passes), which fixes every node's position without a second layout. `ReportPageAction` sends it with the graph fingerprint and the build. The server compares (FR-090): the build with `AppInfoAction`'s, the fingerprint with the held graph's, and the layout hash with the first hash reported for that page and settings in the room.

**Rationale**: one hash serves the tests, the cross-engine tool and the room; nothing exists only for a test.

## R10 — Coordinates, pointers, follow

**Decision**
- Pointers and screen centres travel in **diagram coordinates**: G6 canvas coordinates for the full graph (`getCanvasByClient` / `getClientByCanvas`, present in G6 5.1.1), the SVG's user space for Graphviz (`getScreenCTM()` and its inverse). A shared overlay layer re-projects on every G6 `aftertransform` and on every pan-zoom change of `useSvgPanZoom`, which gains an `onTransform` callback and a `centreOn(point)` method.
- Viewport messages carry the centre and the visible width and height in diagram units; a follower centres on the centre and keeps its own zoom (FR-051).
- History: pages opened by following use `history.replaceState` (FR-057); `lib/urlState.ts` gains a `replace` flag.

## R11 — Page settings in the client

**Decision**: today every viewer keeps its settings in module-level maps keyed by the page (`layoutByDiagramKey`, `enabledDomainsByDiagramKey`, `enabledEntityQualsByDiagramKey`, `disabledKindsByDiagramKey` in `ErdGraphvizCanvas.tsx`; `useCaseLayoutPresetByDomainId`, `useCaseEnabledDomainsByViewKey`, `useCaseBoundaryByDomainId`, `useCaseRankdirByDomainId` in `UseCaseDiagramViewer.tsx`; `lifecycleFsmRankdirByNodeId` in `LifecycleFsmViewer.tsx`; `includeOneHop` state in `ErdViewer.tsx`). They move behind one hook, `usePageSetting(pageKey, name, default)`, which reads and writes the local map outside a room and the room's state inside one, sending "set to" values (FR-031). The full graph has no filter today; its legend is display-only.

## R12 — What the rest of the feature reuses

- **ERD table style** (FR-110 … FR-115): `lib/buildDotSource.ts` already builds HTML-like labels; the change is in the header cell (flush, rounded), the alternating row tint and the key column. Checked by the existing `scripts/check-erd-kinds-and-lines.ts` pattern with a new `check-erd-table-style.ts`.
- **Left panel footer** (FR-100 … FR-102): `LeftSidebar.tsx`, reading `AppInfoAction` once.
- **Documentation** (constitution VI): `docs/tutorials/step-26-maxitor.md` gains a section per case, with `examples/step_26_maxitor/08_rooms.py` / `.ipynb` (rooms through the WebSocket adapter with two clients) and `09_fresh_graphs.py` / `.ipynb` (ETag, 304, a changed source redrawn), following `04_full_graph_delivery`.
