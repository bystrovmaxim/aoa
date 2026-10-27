# Implementation Plan: Maxitor Rooms — Looking at One Service Together

**Branch**: `feature/issue-271-maxitor-rooms` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/028-maxitor-rooms/spec.md` (issue #271), its clarifications of 2026-10-27, and the design mockup [mockup/index.html](mockup/index.html).

## Summary

People open a room from any Maxitor page, share its link, and see each other's pointers, pages and filters; they can go to someone or follow them, at their own zoom. Three things make that hold:

1. **The same picture everywhere.** The full graph is laid out by Maxitor itself, centred at the origin and started from a spiral computed with exact arithmetic only, so every engine and screen size gets bit-identical positions; a mandatory check-run step proves it in Chromium, Firefox and WebKit (research R2, R3).
2. **Everything on the server is an action, everything it touches is a resource** (R1). Rooms run through a new WebSocket route type of the FastAPI adapter that maps each message to an action; the room registry, the graph store, open tabs and the sources are resources; logging goes through `box` (R5, R6).
3. **Graphs stay fresh by themselves.** The adapter answers `ETag` / `304`; Maxitor checks every source that has open tabs through a gateway resource and redraws open pages when the model changes; held graphs stay until the store's limit (R4, R7).

The ERD table style and the left panel's project link travel with the feature (R12).

## Technical Context

**Language/Version**: Python 3.12 (server, adapter); TypeScript 5.7 with React 19 and Vite 6 (client); Node runs `.ts` scripts directly.

**Primary Dependencies**: FastAPI 0.162 / Starlette 1.10 (WebSocket support is Starlette's); uvicorn 0.54; `websockets` 17.3 — already in `uv.lock` as a transitive dependency, becomes a direct dependency of `aoa-maxitor` (BSD-3-Clause, compatible with Apache-2.0); `httpx` 0.28 inside resources only; `@antv/g6` 5.1.1 and `@antv/layout` 2.0.0 (unchanged versions); `@hpcc-js/wasm-graphviz` 1.21.5; `playwright` (dev, already present) for the cross-engine step.

**Storage**: process memory only — the room registry, the graph store, open tabs; IndexedDB in the browser for remembered arrangements (#245), keyed now also by the layout version.

**Testing**: pytest in `packages/aoa-maxitor/tests` and `packages/aoa-fastapi-adapter/tests` (actions with stub resources, the WebSocket route through Starlette's `TestClient`, several connections per room); vitest for the client's pure modules (starting spiral, layout hash, circle rule mirror, initials, coordinate maps) under jsdom; `scripts/check-layout-determinism.ts` in the check run for the three engines; `scripts/check-erd-table-style.ts` for the ERD tables.

**Target Platform**: evergreen browsers on desktop, tablet and phone (V8, JavaScriptCore, SpiderMonkey); the Maxitor container (`python:3.12-slim`) as one process behind the stand's nginx, which must pass WebSocket upgrades.

**Project Type**: web application — FastAPI backend serving a React SPA, plus the shared FastAPI adapter package.

**Performance Goals**: a pointer reaches others within one network round trip plus at most 50 ms of throttling (20 sends a second, FR-043); a changed source redraws open tabs within one check interval (30 s with validators, 2 min without); a check of an unchanged source costs one `304`.

**Constraints**: bit-identical layout hashes across engines and sizes (SC-001); the room never holds a graph (FR-017); records name ids, never names (FR-069); 20 participants per room, 100 rooms per process, 40 messages a second and 4 KB per message (FR-015); no production code exists only for tests — the layout hash on the diagram element serves the room as well (R9).

**Scale/Scope**: the reference graph has 440 nodes and 545 edges; a full process can hold 100 rooms × 20 participants = 2 000 connections. Server: one new model package `aoa/maxitor/model/rooms/`, a few resources and actions beside the existing ones, `app.py` wiring. Adapter: one new route type and one middleware. Client: a room layer (`client/src/rooms/`), one hook for page settings, changes in the four viewers, `LeftSidebar.tsx`, `MainLayout.tsx`, `lib/buildDotSource.ts`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — passes.*

| Principle / rule | How this plan keeps it |
|---|---|
| **I. The maintainer decides** | No phase commits, pushes or opens a pull request by itself; each phase ends with its diff shown and waits for the instruction. |
| **II. English** | Code, comments, docstrings, commit messages, the issue and the documentation are English; Russian exists only as `*.ru_draft.md` beside the spec, the checklist and `tasks.md` (and the documentation page), never committed. |
| **III. Module headers** | Every new Python module (`model/rooms/**`, the adapter's WebSocket module, the new resources and actions) opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` sections. |
| **IV. AI-CORE blocks** | Every new public class — each action, each resource, the adapter route record — carries `ROLE` / `CONTRACT` / `INVARIANTS`; none in a module docstring or on a method. |
| **V. Short docstrings** | Every new class, function and method has its one line. |
| **VI. The tail** | Three last tasks, in this order: the check run to zero, the documentation (every case — joining, refusals, pointers, following and its refusals, reconnect, fresh graphs with `304` and with a content hash, a source that does not answer — as a script and a notebook under `examples/step_26_maxitor/`), the changelog as one article. |
| **Final step: the check run** | The new determinism step is added to `scripts/run_checks_with_log.sh` and taken green with the rest. |
| **Project rule: actions and resources** (maintainer, 2026-10-27) | No hand-written route, no decision in a middleware or a timer, no store or service outside a resource (research R1). The older violations are #278 and are not touched here, except its phase 3, taken into commit 6. |

No violations; Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/028-maxitor-rooms/
├── spec.md, spec.ru_draft.md        # the specification (with clarifications)
├── mockup/index.html                # normative design mockup, 21 screens
├── checklists/requirements.md       # spec quality checklist (+ .ru_draft.md)
├── plan.md                          # this file
├── research.md                      # R1–R12: decisions, rationale, alternatives
├── data-model.md                    # rooms, participants, settings, held graphs, hashes
├── quickstart.md                    # how to see each part work, end to end
├── contracts/
│   ├── websocket-adapter.md         # the adapter's WebSocket route type
│   ├── room-protocol.md             # every message of the room connection, both ways
│   ├── room-actions.md              # actions, resources, refusals and log records
│   ├── http.md                      # ETag / 304, POST rooms, graph fingerprint, app info
│   └── layout-determinism.md        # layout rules, layout hash, the cross-engine step
└── tasks.md                         # Phase 2 (/speckit-tasks), with tasks.ru_draft.md
```

### Source Code (repository root)

```text
packages/aoa-fastapi-adapter/
├── src/aoa/fastapi/
│   ├── adapter.py                   # .websocket(...) registration; conditional-GET middleware in build()
│   ├── websocket_route.py           # NEW: route record, per-connection loop, limits, relay
│   ├── socket_channel.py            # NEW: SocketChannel resource (volatile + ordered queues)
│   └── conditional_get.py           # NEW: ETag / If-None-Match middleware
└── tests/                           # route, limits, relay, 304

packages/aoa-maxitor/
├── pyproject.toml                   # + websockets
├── src/aoa/maxitor/
│   ├── api/
│   │   ├── app.py                   # wiring: rooms route, /api/meta app, check timer, store limit
│   │   └── graph_store.py           # idle timeout removed; swap-on-success; validators kept
│   └── model/
│       ├── rooms/                   # NEW domain
│       │   ├── rooms_domain.py
│       │   ├── resources/room_registry.py, open_tabs_registry.py
│       │   ├── actions/ create, join, leave, rename, set_page_setting, report_page,
│       │   │            follow, stop_following, end_room, expire_participant
│       │   └── follow_circle.py     # pure rule, used by FollowAction
│       └── core/
│           ├── resources/graph_store_controller.py, graph_source_gateway.py,
│           │            static_bundle_resource.py
│           └── actions/ check_source, check_due_sources, graph_fingerprint, app_info
├── tests/                           # rooms, fresh graphs, memory limit, app info
└── client/
    ├── vite.config.ts               # build.json + __MAXITOR_BUILD__
    ├── scripts/check-layout-determinism.ts, check-erd-table-style.ts   # NEW
    └── src/
        ├── rooms/                   # NEW: connection, store, top row, circles, cards,
        │                            #      pointer overlay, edge arrows, follow frame
        ├── lib/pageSettings.ts      # NEW: usePageSetting
        ├── lib/urlState.ts          # room param, replace flag
        ├── components/diagrams/FullGraphViewer/  initialPositions.ts (NEW), layoutHash.ts (NEW),
        │                            forceLayout.ts, layoutSettings.ts, arrangementStore.ts, FullGraphViewer.tsx
        ├── components/diagrams/{ErdViewer,UseCaseDiagramViewer,LifecycleFsmViewer}/  settings + hash + overlay
        ├── components/layout/MainLayout/MainLayout.tsx      # the top row
        ├── components/navigation/LeftSidebar/LeftSidebar.tsx # the footer
        └── lib/buildDotSource.ts    # ERD table style

scripts/run_checks_with_log.sh       # + the determinism step
docs/tutorials/step-26-maxitor.md    # + rooms, fresh graphs
examples/step_26_maxitor/08_rooms.{py,ipynb}, 09_fresh_graphs.{py,ipynb}
deploy/stand/docker-compose*.yml     # MAXITOR_MAX_GRAPHS for the stand (nginx is on the host, outside the repository)
```

**Structure Decision**: the existing layout is kept. Rooms are a new domain package inside Maxitor's model, next to `core` and `diagrams`, so they appear on Maxitor's own graph. The WebSocket route type and the conditional-GET middleware belong to `aoa-fastapi-adapter`, because they are transport for every service, not Maxitor logic. Client room code lives in one folder, `client/src/rooms/`, with a README per component folder as the check run requires.

## Phases (each one commit)

| # | Commit | Requirements | Depends on |
|---|---|---|---|
| 1 | **Design documents**: `specs/028-maxitor-rooms/` | — | — |
| 2 | **The same full-graph layout everywhere**: Maxitor lays out (lazy `forceLayout.ts`, drawn through `PrecomputedLayout`), origin centre, `initialPositions.ts`, `LAYOUT_VERSION` in the fingerprint, `layoutHash.ts`, `data-layout-hash` on all four viewers; guard test and golden hash | FR-001–005 | 1 |
| 3 | **The cross-engine step**: fixture, `check-layout-determinism.ts`, its step in the check run, with a printed `skip` for the pointer case until commit 11 | FR-006 | 2 |
| 4 | **Conditional answers in the adapter**: `ETag`, `304` | FR-070 | 1 |
| 5 | **WebSocket routes in the adapter**: route record, `SocketChannel`, per-connection loop, refusals as close codes, rate and size limits, relay, ordered and volatile queues | FR-066, FR-068 (transport), FR-015 (rate, size) | 1 |
| 6 | **Graph store kept until the limit, as a resource**: idle timeout removed, `GraphStoreController`, swap-on-success; `GraphSourceGateway`, through which `LoadAOAServiceAction` now downloads (#278's phase 3 taken here) | FR-080, FR-081 | 1 |
| 7 | **Fresh graphs on the server**: validators in the gateway, `CheckSourceAction`, `CheckDueSourcesAction`, the timer, `OpenTabsRegistry`, `GraphFingerprintAction` | FR-071–075, FR-077 | 4, 6 |
| 8 | **Rooms on the server**: `RoomsDomain`, `RoomRegistry`, the room actions, follow-circle rule, two-minute return, end of an empty room, limits, origin refusal, logging, the fingerprint in the sidebar answer, `AppInfoAction` and `/api/meta`, the route wiring, `websockets` dependency | FR-010–019, FR-054 (server), FR-060–069, FR-090 (server) | 5, 6 |
| 9 | **Joining and the top row**: room connection with reconnect, name dialog and its notice, `room` in the address, Copy link (share sheet, hand-copy field), Leave, Change name, full room, ended room, *Load a different service* question, top row on desktop and phone, circles, cards, +N, notices, keyboard access | FR-019–028, FR-060–065 | 8 |
| 10 | **Shared page settings**: `usePageSetting` in all four viewers | FR-030–033 | 9 |
| 11 | **Pointers and out-of-date tabs**: overlay in diagram coordinates, edge arrows, throttling (pointer 20/s, screen 10/s), idle fade, hidden while offline, Hide pointers, build / fingerprint / layout checks and their outcomes; the pointer case of the cross-engine step replaces its `skip` | FR-040–045, FR-090–093, SC-003 | 2, 9 |
| 12 | **Pages redraw on a new graph**: fingerprint poll outside a room, the room's announcement inside, re-read keeping page, settings, zoom and centre, *The model was updated* | FR-076 | 7, 9 |
| 13 | **Going to someone**: Go to from a circle, a card or an edge arrow, at your own zoom | FR-050 | 11 |
| 14 | **Following**: Follow, Follow instead, Stop / Esc, frame, the circle rule in the card, follower counter, history replaced | FR-051–057 | 13 |
| 15 | **ERD table style** | FR-110–115 | 1 |
| 16 | **Left panel footer** | FR-100–102 | 8 (`AppInfoAction`) |
| 17 | **Closing check run** — `bash scripts/run_checks_with_log.sh` to zero | constitution VI.1 | all |
| 18 | **Documentation** — `step-26-maxitor.md` sections, the stand's nginx lines, and the two examples as scripts and notebooks, executed while written, with the Russian draft of the page | constitution VI.2, VI.4–7 | 17 |
| 19 | **Changelog** — one article in `docs/CHANGELOG.md` | constitution VI.3 | 18 |

Commits 2–3, 4–7, 15 and 16 can be built in any order relative to each other; 9–14 follow 8. tasks.md uses the same numbering.

## Risks

- **`D3ForceLayout` and starting positions.** If the wrapper drops `x`/`y`, the spiral of `d3-force-3d` returns with `cos`/`sin`. The guard test catches it in commit 2; the fallback is to call `d3-force-3d` directly with the same forces.
- **The picture changes once.** A new starting spiral and centre give a slightly different full graph than today's; the golden hash is recorded once in commit 2 and the canvas comparison of #245 (`data/canvas-main.png`) is re-recorded on purpose.
- **Playwright browsers in the check run.** Three browsers add download time and disk; on Linux they need system packages. Today's check run is local on macOS (R3).
- **nginx and WebSocket.** The stand's nginx runs on the host, outside this repository (`deploy/stand` only publishes the container port). It must forward `Upgrade`/`Connection` for `/api/v1/rooms/`, or the room never connects; the lines are recorded in tasks.md (T056) and documented in commit 18, and the maintainer applies them on the host.
- **Memory without the idle timeout.** The process stays at its peak; `MAXITOR_MAX_GRAPHS` for the stand must fit the machine (R7).
- **#278's phase 3 is taken here.** `LoadAOAServiceAction` downloads through `GraphSourceGateway` from commit 6 on, so the new validators and content hash never come from `httpx` inside an aspect; #278 records that its phase 3 is done by #271.
- **`/api/v1` and the legacy middleware.** Until #278, every `/api/v1` HTTP path demands `source`; `GET /api/v1/graph-fingerprint` takes it anyway (rooms are opened over the room connection, not by `POST`), and the source-less `AppInfoAction` lives under `/api/meta` (R8).

## Complexity Tracking

> No constitution violations to justify.
