# Contract: actions, resources and log records

Every operation below is an AOA action run by Maxitor's machine; every store and service it touches is a resource in `connections` (research R1). All actions carry `@check_roles(GuestRole)` and `@meta(domain=...)`.

## Resources

| Key | Class | Kind | Owns |
|---|---|---|---|
| `RoomRegistry` | `RoomRegistry` | `BaseController` | rooms, participants, tabs, page settings, follow links, return windows, room timers; `relay(channel, message)` for pointers and viewports |
| `OpenTabs` | `OpenTabsRegistry` | `BaseController` | source → last time a tab outside a room asked for the fingerprint |
| `GraphStore` | `GraphStoreController` | `BaseController` | held graphs, build slots, swap-on-success |
| `GraphSource` | `GraphSourceGateway` | `BaseGateway` | `httpx`; `fetch(url)` → `Document(body, etag, last_modified, sha256)` / `Unreachable(reason)`; `fetch_if_changed(url, etag, last_modified)` also → `NotModified` (commit 7: two methods, so the first load never handles a `304` it cannot get) |
| `StaticBundle` | `StaticBundleResource` | `BaseStorage` | the installed client bundle; reads `build.json` |
| `SourceChecks` | `SourceChecks` | `BaseController` | the clock (every 10 s, `CheckDueSourcesAction`) and `run_soon` for one background `CheckSourceAction`; started and closed by the lifespan (commit 7) |
| `socket` | `SocketChannel` | `BaseController` | one connection (contracts/websocket-adapter.md) |

Resources hold state and do I/O; they decide nothing. Every rule below is checked in an aspect.

## Room actions (domain `RoomsDomain`)

| Action | Run by | Params | Rule checked in the aspect | Refusal |
|---|---|---|---|---|
| `JoinRoomAction` | WebSocket `on_open` | `room_id`, `participant`, `tab`, `participant_name`, `start_page`, `source`, `origin`, `host` | `origin` is empty, listed, or of the request's host (FR-016); name valid; `room_id` `new`: `source` given, rooms < 100, the source builds — then the room opens; otherwise the room exists; participants < 20 unless returning; page exists for the source, else `fallback_page` (FR-010) | close `4403`, `4404`, `4409`, `4422`, `4502`, `4503` |
| `LeaveRoomAction` | `leave` | — | the participant leaves at once: every tab closes, followers stop, `left` to the room | — |
| `DisconnectTabAction` | `on_close` | — | a tab's connection ended without `leave`; the last tab of a participant opens the two-minute window (`away`) instead of leaving | — |
| `ExpireParticipantAction` | registry timer | `room_id`, `participant` | the window really expired and the participant did not return | — |
| `EndRoomAction` | registry timer | `room_id` | the room is still empty after two minutes | — |
| `RenameParticipantAction` | `rename` | `name` | name valid | `refused 4422` |
| `ReportPageAction` | `page`, `activity` | page, build, fingerprint, layout hash, digest, visible | compares build with `StaticBundle`, fingerprint with `GraphStore`, layout hash with the room's first for that page and digest | — (answers `check`) |
| `SetPageSettingAction` | `setting` | `page`, `name`, `value` | `name` is a known setting of that page; `value` has its type | `refused 4422` |
| `FollowAction` | `follow` | `target` | target present and not self; no circle (data-model.md, FollowLink), checked and written under the room lock | `follow_refused` |
| `StopFollowingAction` | `stop_following` | — | — | — |
| `ReloadSourceForRoomAction` | `reload` | — | the participant is in a room of that source; runs `CheckSourceAction(force=True)` through `box.run`, which rebuilds and announces `graph_changed` | `refused 4502` when the build fails; the old graph stays |

## Graph actions (domain `CoreDomain`)

| Action | Run by | Does |
|---|---|---|
| `CheckSourceAction` | `CheckDueSourcesAction`, reads, `ReloadSourceForRoomAction` | asks `GraphSource` with the held validators; unchanged (`304` or same SHA-256) → records the check; changed → builds through `GraphStore` and swaps on success, then tells `RoomRegistry` to announce `graph_changed`; unreachable or failed build → keeps the old graph |
| `CheckDueSourcesAction` | lifespan timer, every 10 s | picks held sources with open tabs whose last check is older than 30 s (with validators) or 2 min (without); runs `CheckSourceAction` for each, never two for one source |
| `GraphFingerprintAction` | `GET /api/v1/graph-fingerprint?source=` | records the tab in `OpenTabs`; returns the held fingerprint; starts a background check when the last one is older than its interval (FR-073) |
| `AppInfoAction` | `GET /api/meta/app-info` | returns `version` (installed `aoa-maxitor`) and `build` (`StaticBundle`) |

## Log records

Written through `box` in the aspects. Records name rooms and participants by id only (FR-069); pointers and viewports are never logged (FR-068).

| Event | Call | Variables |
|---|---|---|
| room created | `box.info(Channel.business, ...)` | `room`, `source` |
| room ended | `box.info(Channel.business, ...)` | `room`, `participants_at_peak` |
| joined / returned / left / expired | `box.info(Channel.business, ...)` | `room`, `participant`, `participants` |
| refused: room full, too many rooms, invalid name, room ended | `box.warning(Channel.security, ...)` | `room`, `limit` or `reason` |
| refused: foreign origin | `box.warning(Channel.security, ...)` in `JoinRoomAction` | `room`, `origin` |
| follow refused (circle) | `box.warning(Channel.security, ...)` | `room`, `participant`, `target` |
| source unchanged / changed / unreachable / build failed | `box.info` / `box.info` / `box.warning(Channel.error)` / `box.warning(Channel.error)` | `source`, `status` |
| internal failure in any room action | not written by the action: the machine raises `UnhandledErrorEvent` for logging plugins and the adapter closes `1011` | — |

An aspect cannot log its own unexpected failure: `@on_error(Exception)` would also catch the planned refusals (`ConnectionRefusalError`), and a handler that re-raises turns them into `OnErrorHandlerError`, so the client would get `1011` instead of `4409` or `4422`. `box.critical` is therefore not used by room actions (commit 8).
