# Contract: actions, resources and log records

Every operation below is an AOA action run by Maxitor's machine; every store and service it touches is a resource in `connections` (research R1). All actions carry `@check_roles(GuestRole)` and `@meta(domain=...)`.

## Resources

| Key | Class | Kind | Owns |
|---|---|---|---|
| `RoomRegistry` | `RoomRegistry` | `BaseController` | rooms, participants, tabs, page settings, follow links, return windows, room timers; `relay(channel, message)` for pointers and viewports |
| `OpenTabs` | `OpenTabsRegistry` | `BaseController` | source → last time a tab outside a room asked for the fingerprint |
| `GraphStore` | `GraphStoreController` | `BaseController` | held graphs, build slots, swap-on-success |
| `GraphSource` | `GraphSourceGateway` | `BaseGateway` | `httpx`; `fetch(url, etag, last_modified)` → `NotModified` / `Document(body, etag, last_modified, sha256)` / `Unreachable(reason)` |
| `StaticBundle` | `StaticBundleResource` | `BaseStorage` | the installed client bundle; reads `build.json` |
| `socket` | `SocketChannel` | `BaseController` | one connection (contracts/websocket-adapter.md) |

Resources hold state and do I/O; they decide nothing. Every rule below is checked in an aspect.

## Room actions (domain `RoomsDomain`)

| Action | Run by | Params | Rule checked in the aspect | Refusal |
|---|---|---|---|---|
| `CreateRoomAction` | `POST /api/v1/rooms?source=` | `source`, `participant`, `name`, `page` | name 1–40 after trim; rooms < 100 | `422 invalid name`; `503 too many rooms` |
| `JoinRoomAction` | WebSocket `on_open` | `room_id`, `participant`, `tab`, `name`, `page`, `origin` | `origin` is the address Maxitor serves (FR-016); room exists; participants < 20 unless returning; name valid; page exists for the source, else `fallback_page` (FR-010) | close `4403`, `4404`, `4409`, `4422` |
| `LeaveRoomAction` | `on_close`, `leave` | — | clean leave vs lost connection: a lost one opens the two-minute window instead of leaving | — |
| `ExpireParticipantAction` | registry timer | `room_id`, `participant` | the window really expired and the participant did not return | — |
| `EndRoomAction` | registry timer | `room_id` | the room is still empty after two minutes | — |
| `RenameParticipantAction` | `rename` | `name` | name valid | `refused 4422` |
| `ReportPageAction` | `page`, `activity` | page, build, fingerprint, layout hash, digest, visible | compares build with `StaticBundle`, fingerprint with `GraphStore`, layout hash with the room's first for that page and digest | — (answers `check`) |
| `SetPageSettingAction` | `setting` | `page`, `name`, `value` | `name` is a known setting of that page; `value` has its type | `refused 4422` |
| `FollowAction` | `follow` | `target` | target present and not self; no circle (data-model.md, FollowLink), checked and written under the room lock | `follow_refused` |
| `StopFollowingAction` | `stop_following` | — | — | — |
| `ReloadSourceForRoomAction` | `reload` | — | the participant is in a room of that source; runs `CheckSourceAction(force=True)` through `box.run` | as `CheckSourceAction` |

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
| internal failure in any room action | `box.critical(Channel.error, ...)` | `room`, `action` |
