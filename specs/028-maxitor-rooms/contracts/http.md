# Contract: HTTP

## Conditional answers of every adapter `GET` (FR-070)

Package `aoa-fastapi-adapter`; applies to every app built by `FastApiAdapter.build()`.

| Request | Answer |
|---|---|
| `GET` → status 200, any body | adds `ETag: "<first 32 hex of SHA-256 of the body>"` |
| `GET` with `If-None-Match` equal to that tag (or a list containing it, or `*`) | `304 Not Modified`, empty body, same `ETag` |
| any other method or status | unchanged |

The tag is taken over the body after the endpoint and before compression, so a gzip layer outside does not change it. A restart with the same content gives the same tag.

## New Maxitor endpoints

All run actions through `FastApiAdapter` (contracts/room-actions.md). Until #278, every `/api/v1` path passes `GraphSourceMiddleware`, so `graph-fingerprint` takes `source` like every graph read.

### Opening a room — no HTTP endpoint

A room is opened by connecting to `GET /api/v1/rooms/new/live?source=<graph-json URL>&…` (contracts/room-protocol.md): `JoinRoomAction` builds the source, opens the room and answers `welcome` with its id, and the page puts `room=<id>` into its address. One action and one connection instead of a `POST` followed by a connect, so a room never exists without its first participant (commit 8). Its refusals are close codes: `4422` invalid name, `4503` too many rooms, `4502` the source cannot be built now.

### `GET /api/v1/graph-fingerprint?source=<graph-json URL>`

`200 {"fingerprint": "<SHA-256 of the graph-json body>"}`. Answered from memory; records an open tab for the source; may start a background check (FR-073). Called every 30 s by a tab outside a room (FR-076).

### `GET /api/sidebar?source=…` (existing)

Its answer gains one field, `"fingerprint"`: the fingerprint of the held graph it was read from, the same value `graph-fingerprint` returns. The client keeps it as the fingerprint of the graph it drew (FR-090). The route itself stays as it is until #278.

### `GET /api/meta/app-info`

A second adapter app mounted at `/api/meta`, outside the middleware's paths. `200 {"version": "2.2.0", "build": "<12 hex>"}` (FR-090, FR-101).

## Room connection upgrade

`GET /api/v1/rooms/{room_id}/live` with `Upgrade: websocket` — contracts/websocket-adapter.md and contracts/room-protocol.md. The stand's nginx (on the host) must forward `Upgrade` and `Connection` for `/api/v1/rooms/`.
