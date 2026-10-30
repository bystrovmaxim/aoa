# Implementation Plan: Maxitor Opens a History and Shows Any Version

**Branch**: `feature/issue-289-open-history-any-version` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/037-history-one-version/spec.md` (issue #289, step 4 of 9 of #273)

## Summary

Maxitor learns to open a history as well as a graph. A private history's address is the port's history URL with the key in the fragment (`…/api/v1/history/orders#key=…`), a public one is the GitHub link to its graph file, and a running service is its own address; both are read only through `repo-graph-port`, which gains an optional `live` per history and returns it, with the key's name, from `describe`. The key lives in the browser and travels to Maxitor only in a header, never in a URL or a log. Each version is built once into `GraphStore` under the port's version URL, shared between readers whose key the port accepted, and never checked again; the history's list is held in a new `HistoryStore` and checked every 30 seconds by `ETag`. The client gets a version button, a picker with one scrolling track and the version's message, the key shown as dots with an eye, Recent that says what each address was, and the phone's sheet. In a room the version is the room's, like a page's settings. Every combination of Live and versions — seven modes, M1–M7 — is specified and tested.

## Technical Context

**Language/Version**: Python ≥ 3.12 (server, port); TypeScript 5.7, React 19, MUI (client).

**Primary Dependencies**: AOA (`aoa-action-machine`, `aoa-fastapi-adapter`), `httpx`, DuckDB (existing); no new dependency on either side.

**Storage**: none new on the server (process memory: `GraphStore`, `HistoryStore`, `HistoryAccess`); the browser's own storage — `localStorage` for Recent, `sessionStorage` for the tab's key; the port's histories config (TOML) gains `live`.

**Testing**: pytest with a stand-in port (`httpx.MockTransport`); the port's own suite; vitest + Testing Library; the boundary checker; the check run.

**Target Platform**: Maxitor's server and its browser client, desktop and phone; the stand.

**Project Type**: web application (Maxitor's server + its client) and a field added to a web service (the port).

**Performance Goals**: a version is built once whatever the number of readers; an unchanged history list costs a `304`; a held version for an accepted key costs no port request for 30 s; a track of 500 points opens with the chosen version in view and its labels never overlap (T034).

**Constraints**: the key never in a URL, a source string, a log (including uvicorn's access log), an error text, the browser's address bar or history, or any storage but the user's own `localStorage` and `sessionStorage`, or a `Referer`; the front never imports the port (`scripts/package_boundaries.toml`); every endpoint is an AOA action; a message is never set as HTML.

**Scale/Scope**: about 12 server modules touched or added, about 15 client components and libraries, 3 port modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The maintainer decides | Each phase is a commit made only on the maintainer's word; no push, PR or merge without it. | ✅ |
| II. English | Code, docs, commits in English; only `tasks.ru_draft.md` and the documentation's `*.ru_draft.md` in Russian. | ✅ |
| III. Module headers | Every new module opens with its path, title and `PURPOSE` / `ARCHITECTURE / DATA FLOW`. | ✅ |
| IV. AI-CORE blocks | Every new public action, resource and store carries one; methods get one line. | ✅ |
| V. Short docstrings | Every class, function and method, server and client. | ✅ |
| VI. Tail | Phase 7 is three commits: the check run, the documentation (how-to page with every mode and refusal, an executed example as script and notebook, READMEs, Russian draft), the changelog article. | ✅ |
| Final step: the check run | Taken to zero; the two accepted remarks stay. | ✅ |

House rules: endpoints only through actions — the two history routes and the room's `version` message are actions (`OpenHistoryAction`, `HistoryVersionsAction`, `SetRoomVersionAction`, `CheckHistoryAction`); the port is reached only through a resource (`RepoGraphPortGateway`). ✅

No violations; Complexity Tracking stays empty. **Re-checked after Phase 1**: the contracts add no route outside an action and no import across the boundary. ✅

## Project Structure

### Documentation (this feature)

```text
specs/037-history-one-version/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── maxitor-api.md     # the history routes, the changed graph reads, the logs
│   ├── port.md            # `live` in the config, `live` and `reader` in describe
│   ├── room-protocol.md   # rooms on a history: `version`, `history_changed`
│   └── ui.md              # modes M1–M7 and every part of the screen
├── checklists/requirements.md
└── tasks.md (+ tasks.ru_draft.md)
```

### Source Code

```text
packages/maxitor/
├── tools/repo_graph_port/src/maxitor/repo_graph_port/
│   ├── history.py                         # History gains `live`
│   ├── resources/histories_config.py      # `live` read and checked
│   ├── actions/describe_history_action.py # `live`, `reader`
│   ├── auth/history_key_auth_coordinator.py  # the wrong-key and block events (FR-011f)
│   └── webhook_signature_middleware.py    # the wrong-signature event (FR-011f)
├── front/src/maxitor/front/
│   ├── api/
│   │   ├── app.py                         # the `/api/history` sub-app; uvicorn's access log without queries
│   │   ├── main.py                        # the access-log format
│   │   ├── graph_store.py                 # `immutable`; acquire(source, key=)
│   │   ├── graph_source_middleware.py     # version sources: key header, access, refused
│   │   └── history_store.py               # new: HistoryStore, HistoryEntry
│   └── model/
│       ├── core/
│       │   ├── freshness.py               # immutable entries never due
│       │   ├── source_label.py            # new: origin#hash
│       │   ├── history_address.py         # new: parse a history's address
│       │   ├── actions/
│       │   │   ├── load_aoa_service_action.py   # bare graph
│       │   │   ├── check_source_action.py       # labels, not addresses
│       │   │   ├── check_due_sources_action.py  # due histories too
│       │   │   ├── open_history_action.py       # new
│       │   │   ├── history_versions_action.py   # new
│       │   │   └── check_history_action.py      # new
│       │   └── resources/
│       │       ├── graph_source_gateway.py      # optional key header
│       │       ├── repo_graph_port_gateway.py   # new: describe, versions (ETag)
│       │       └── history_access.py            # new: accepted keys, 30 s
│       └── rooms/
│           ├── resources/room_registry.py       # Room.history, Room.version
│           └── actions/
│               ├── join_room_action.py          # open on a history; welcome
│               └── set_room_version_action.py   # new
│   └── tests/                                   # stand-in port; every mode
└── front/client/src/
    ├── lib/
    │   ├── urlState.ts                    # `history`, `b`, `#key`
    │   ├── serviceUrlHistory.ts           # Recent records
    │   ├── historyAddress.ts              # new: parse, mask, the copied link
    │   ├── historyKey.ts                  # new: `#key=` to `sessionStorage`, out of the address bar
    │   ├── versionNames.ts                # new: R10
    │   └── linkify.ts                     # new: R12
    ├── api/history.ts                     # new: the two routes, key header, ETag
    ├── model/historyMode.ts               # new: M1–M7
    ├── components/history/                # new, each with README and index.ts
    │   ├── VersionButton/
    │   ├── VersionPicker/
    │   ├── VersionTrack/
    │   └── VersionMessage/
    ├── components/navigation/LeftSidebar/ServiceUrlInput.tsx  # dots, eye, Recent
    ├── app/App.tsx                        # the history state; the top row and the phone bar
    └── rooms/                             # protocol, roomStore, useRoomSession: version
```

Outside: `docs/how-to/open-a-graph-history.md` (+ `.ru_draft.md`), `examples/step_26_maxitor/` (script + notebook), the front's and the port's READMEs, `docs/CHANGELOG.md`; the stand's histories config gets `live` for the maintainer's histories; `deploy/stand/docker-compose*.yml` gets `maxitor-public-port` — the port's image with an empty histories config and its own cache volume, on Maxitor's internal network, no published port — and Maxitor's service gets `MAXITOR_PUBLIC_PORT` (research R16).

**Structure Decision**: the existing web application — server under `front/src/maxitor/front/`, client under `front/client/src/` — with the history pieces beside the graph pieces they mirror; the port changes only by its two fields.

## Phases → commits

| # | Phase (issue #289, §6) | Contents | Proof | Adversarial break |
|---|---|---|---|---|
| 0 | Design documents | `specs/037-history-one-version/` | — | — |
| 1 | Reading a history | port: `live`, `reader`; server: address parsing, `RepoGraphPortGateway`, `HistoryStore`, `HistoryAccess`, the two history actions and routes, version sources in the middleware, bare graph, `immutable`, `CheckHistoryAction` on the clock, labels in logs, access log without queries; rooms: `history`, `version`, `SetRoomVersionAction`, `history_changed`, the room ticket (R18); public links through `MAXITOR_PUBLIC_PORT` (R16), refused when unset; moves between modes (`live` added or removed, a version gone) | server tests for M1–M7; a wrong key is `404`; a held version with a revoked key is refused within 30 s; a version is built once for two keys; an unchanged list is a `304`; the key in no log line, error body or request line; a room join without a valid ticket learns nothing | log the whole source → the no-key-in-log test fails; drop the access check → the revoked-key test fails; let `is_due` pick immutable entries → the freshness test fails |
| 2 | Read keys as dots | `historyAddress.ts`, the field (eight dots), Recent records (removable), the eye, the room link, `#key=` moved to `sessionStorage` and cleared from the address bar, **Copy link** | client tests: dots in field, Recent, room link; eye reveals and hides | render the raw address → the dots test fails |
| 3 | The version button and the picker | `historyMode.ts`, `versionNames.ts`, `VersionButton`, `VersionPicker`, `VersionTrack` (points, releases, flags, tooltip, Live gap, keyboard), mode switch, address bar `history`/`b`/`#key`, App wiring, rooms on the client | client tests per mode M1–M7; names per R10; `b` restored, a wrong `b` falls back | treat `live` as present when absent → M2/M3 tests fail |
| 4 | A long history | sideways scroll, fades, "+N newer", pinned handle, label thinning, opening in view | 64-point and 500-point tests | drop the 24 px minimum → the spacing test fails |
| 5 | The message | `linkify.ts`, `VersionMessage` | `## `, `**`, `<script>`, `javascript:` stay text; `https://` and `#142` link with `noopener noreferrer`; nine-line cap | set the message as HTML → the `<script>` test fails |
| 6 | Phone | the button in the phone bar, the sheet, 44 px targets | phone-width tests | 24 px targets on a phone → the touch-target test fails |
| 7a | Check run | `bash scripts/run_checks_with_log.sh` to zero | green log | — |
| 7b | Documentation | how-to with every mode M1–M7 and every refusal, example script + notebook (executed), READMEs, `.ru_draft.md` | examples run | — |
| 7c | Changelog | one article | — | — |

## Complexity Tracking

No constitution violations.
