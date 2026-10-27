# Data Model: Maxitor Rooms

Everything here lives in the memory of one Maxitor process or in the browser. Nothing is persisted on the server; a restart ends every room (spec, edge cases).

## Room

Held by `RoomRegistry` (a `BaseController` resource).

| Field | Type | Rule |
|---|---|---|
| `id` | string | 128 random bits, `secrets.token_urlsafe(16)` (22 characters); unique in the process |
| `source` | string | the `graph-json` URL the room belongs to; fixed at creation (FR-010) |
| `created_by` | participant id | who opened it; carries no rights (FR-018); used only to choose a fallback page (FR-010) |
| `participants` | map id → Participant | at most 20 (FR-015) |
| `page_settings` | map page key → PageSettings | per page (FR-030) |
| `reported_hashes` | map (page key, settings digest) → layout hash | the first hash reported for that page and settings (FR-093) |
| `empty_since` | time or none | set when the last participant leaves; the room ends 2 minutes later (FR-014) |
| `lock` | `asyncio.Lock` | every change of the room happens under it (FR-054) |

**Lifecycle**: `open` (created by `CreateRoomAction`) → `occupied` (≥ 1 participant) ⇄ `empty` (0 participants, timer running) → `ended` (timer fired: `EndRoomAction`, or the process stopped). An ended id is never reused. The process holds at most 100 rooms (FR-015).

## Participant

| Field | Type | Rule |
|---|---|---|
| `id` | string | random, created by the browser and kept in `localStorage` per room id, so every tab of one browser is one participant (FR-013) |
| `name` | string | 1–40 characters after trimming (FR-011); may repeat in a room; never written to the log (FR-069) |
| `colour` | palette index | the first free index of the room's palette; unique in the room; freed on leave (FR-012) |
| `tabs` | map tab id → Tab | one or more |
| `active_tab` | tab id | the tab with the latest activity (FR-013) |
| `follows` | participant id or none | at most one (FR-053); the set of all `follows` links in a room has no circle (FR-054) |
| `return_until` | time or none | set when the last tab's connection drops; within it the participant keeps id, name, colour and page (FR-062) |

**Lifecycle**: `joining` (name dialog, nothing shown to others) → `present` → `away` (connection lost, `return_until` running, shown as present, pointers hidden) → `present` again, or `left` (window expired: `ExpireParticipantAction`; or **Leave room**; or last tab closed cleanly). On `left`: the circle goes, the colour is freed, and everyone who followed them stops following.

## Tab

| Field | Type | Rule |
|---|---|---|
| `id` | string | random per tab, kept in `sessionStorage` |
| `channel` | `SocketChannel` | the connection's resource (contracts/websocket-adapter.md) |
| `page` | PageKey | the page the tab shows |
| `last_activity` | time | updated by pointer movement, touch, navigation and arrival by link (FR-013) |
| `visible` | bool | from `visibilitychange`; a hidden active tab draws the circle pale (FR-044) |
| `build`, `fingerprint`, `layout_hash` | strings | as last reported for its page (FR-090) |
| `pointer` | Pointer or none | volatile, relayed, never stored beyond the last value |
| `viewport` | Viewport or none | volatile, relayed; used by Go to and Follow |

## PageKey

The page as the address names it (`client/src/lib/urlState.ts`): `view` plus its parameters — `domain` for `domain-erd` and `use-case`, `node` and `host` for `lifecycle-fsm`, nothing for `full-graph`. Serialized canonically as `view` followed by the parameters in that fixed order, `&`-joined. The `source` is the room's and is not part of the key.

## PageSettings

One page's shared settings in one room. Values are "set to", never toggles (FR-031); the last change wins.

| Page | Setting | Value |
|---|---|---|
| ERD (`domain-erd`) | `layout` | one of `gv-dot-lr`, `gv-dot-tb`, `gv-neato`, `gv-fdp`, `gv-circo` |
| | `domains` | the set of enabled domain qualnames |
| | `entities` | the set of enabled entity qualifiers |
| | `disabled_kinds` | the set of switched-off entity kinds |
| | `one_hop` | bool |
| Use case (`use-case`) | `layout` | one of `dot_lr`, `dot_tb`, `neato`, `fdp` |
| | `rankdir` | `LR` or `TB` (`DomainUseCaseRankdir` in `lib/buildDomainUseCaseDotSource.ts`) |
| | `domains` | the set of enabled domains |
| | `boundary` | bool |
| Lifecycle (`lifecycle-fsm`) | `rankdir` | `LR` or `TB` |
| Full graph | — | none today; a filter added later joins by the same rule (spec, assumptions) |

The **settings digest** is SHA-256 over the canonical JSON of a page's settings; with the page key it identifies one picture, so layout hashes are compared only between tabs that should draw the same thing.

## Pointer and Viewport

| Entity | Fields | Rule |
|---|---|---|
| Pointer | `kind` (`mouse` / `touch`), `x`, `y` in diagram coordinates, `t` | sent at most 20 times a second and only when moved (FR-043); fades after 10 s without movement (FR-044) |
| Viewport | `cx`, `cy` (centre), `w`, `h` (visible size), all in diagram units | sent on change, throttled like pointers; a follower uses `cx`, `cy` only, never `w`, `h` as a zoom (FR-051) |

Diagram coordinates: G6 canvas coordinates for the full graph; the SVG's user space for the Graphviz diagrams (research R10).

## FollowLink

`a follows b`, stored as `Participant.follows`. **Invariant**: following the links from any participant never returns to them. `FollowAction(a → b)` is refused when `b`, following its own links, reaches `a` (a direct or indirect follower of `a`). The check and the write happen under the room lock.

## Held graph (extends today's `GraphEntry`)

Held by `GraphStore`, reached through `GraphStoreController`.

| Field | Type | Rule |
|---|---|---|
| `source` | string | key |
| `graph`, `sidebar` | as today | the built DuckDB graph and sidebar result |
| `fingerprint` | string | equal to `content_sha256`: the SHA-256 of the `graph-json` body the graph was built from; two graphs built from equal bodies have equal fingerprints (FR-076, FR-090) |
| `content_sha256` | string | SHA-256 of the downloaded `graph-json` body it was built from (FR-072) |
| `etag`, `last_modified` | strings or none | the source's validators, if it gave any |
| `last_read` | time | for least-recently-read eviction beyond `MAXITOR_MAX_GRAPHS` (FR-080) |
| `last_checked` | time | when the source was last asked; drives FR-071 / FR-073 |
| `checking` | bool | a check of this source is running; checks never overlap (FR-074) |

**Replacement**: a changed source is built into a new entry; the store swaps it in only after the build succeeded. A read in flight keeps the entry it started with (the #214 rule).

## Open tabs

Held by `OpenTabsRegistry` (a `BaseController`): source → last time a tab outside a room asked `GraphFingerprintAction`. A source **has open tabs** when it has a room connection or was asked within 75 s.

## Hashes and builds

| Value | Made of | Where |
|---|---|---|
| Layout hash, full graph | SHA-256 of the positions as little-endian `Float64` pairs in payload order | `layoutHash.ts`; `data-layout-hash` on the diagram element |
| Layout hash, Graphviz | SHA-256 of the SVG markup Graphviz returned for the page's DOT | same attribute |
| Arrangement fingerprint | node ids and types, edges, `LAYOUT_SETTINGS`, `LAYOUT_VERSION` | `arrangementStore.ts` (IndexedDB key) |
| Graph fingerprint | SHA-256 of the `graph-json` body (= `content_sha256`) | server; carried by the sidebar answer and by `GraphFingerprintAction` |
| App build | SHA-256 of the bundle's `index.html`, 12 hex | `build.json` beside the bundle; `__MAXITOR_BUILD__` in the page; `AppInfoAction` |

## Browser-side state

| Key | Storage | Content |
|---|---|---|
| `maxitor.name` | `localStorage` | the last name used (FR-011) |
| `maxitor.room.<id>.participant` | `localStorage` | the participant id for that room (FR-013) |
| `maxitor.tab` | `sessionStorage` | this tab's id |
| `maxitor.hidePointers` | `localStorage` | the Hide pointers switch (FR-026) |
| `maxitor.view.restore` | `sessionStorage` | zoom and centre kept across a self-reload (FR-091) |
| `maxitor.reload.at` | `sessionStorage` | the time of the last self-reload, at most once in 5 minutes (FR-091) |
