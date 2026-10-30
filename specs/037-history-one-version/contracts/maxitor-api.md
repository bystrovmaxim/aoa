# Contract: Maxitor's server for histories

Every route is an AOA action behind Maxitor's `FastApiAdapter`. A private history's key comes only in the header `X-Maxitor-History-Key`; it is extracted by the adapter's auth coordinator into the request's context as a sensitive value and never appears in a URL, a log or an error.

## New: `/api/history` (its own sub-app, outside `GraphSourceMiddleware`)

| Route | Action | Input | Answer |
|---|---|---|---|
| `GET /api/history/open?history=<name>` | `OpenHistoryAction` | the history's name (its address without the key); the key in the header | `{name, title, host, repository, live, live_same_as, versions: [Version…], proposals: [Version…], count, room_ticket}`; `ETag`; `room_ticket` only for a private history (research R18) |
| `GET /api/history/versions?history=<name>` | `HistoryVersionsAction` | the name; `If-None-Match` | `{versions: [Version…], proposals: [Version…], live, live_same_as}`; `ETag`; `304` when unchanged |

`Version` is the port's (`sha, date, pr, message, tags, nodes, edges, refused, contribution, change`, see `port.md`), with the `source` its graph is read under. `proposals` are the port's open pull requests, each with its `source`. `live_same_as` is the newest unrefused version's sha when Live runs exactly its graph — compared as graphs, the same nodes and edges in any order, a service's `coordinator_json` unwrapped — and `null` otherwise or when either cannot be read (FR-036).

Refusals:

| Case | Status | Body |
|---|---|---|
| a name that is neither a port's history URL nor a GitHub blob link to a graph file | `400` | `{"detail": "<what is wrong with it>"}` — the address is not echoed |
| wrong, revoked or expired key; unknown history; key missing for a private one | `404` | `{"detail": "not found"}` |
| the port blocked this client (`429`) | `429` | `{"detail": "Too many wrong keys for this history; try again in a minute"}`; Maxitor does not retry |
| the port unreachable | `503` | `{"detail": "The history cannot be read now."}`, `Retry-After: 5` |

## Changed: graph reads `/api/v1/*` and `/api/sidebar`

`?source=` may now be a version's source (research R4): `<port>/api/v1/history/<id>/versions/<sha>` or `<port>/api/v1/history/public/versions/<sha>?link=<link>`. For such a source `GraphSourceMiddleware`:

1. reads `X-Maxitor-History-Key`;
2. asks `HistoryAccess` whether the key was accepted for that history in the last 30 s, else asks the port (R6) — refused → `404 {"detail": "not found"}`;
3. a version the history lists as `refused` → `422 {"detail": "<the port's reason>"}`;
4. `store.acquire(source, key=…)` — the key is handed to the builder for a first build only.

A Live source and every other source behave as today.

## Changed: `LoadAOAServiceAction`

Accepts the envelope (`coordinator_json`) or a bare graph (`nodes` and `edges` at the top). Its result gains nothing.

## Changed: logs

| Today | After |
|---|---|
| `Source http://host:8001/examples/model/graph-json rebuilt` | `Source http://host:8001#3f9a1c2b rebuilt` |
| — | `History orders by anna opened, 12 versions and Live` |
| — | `History public owner/repo checked, unchanged` |
| — | `box.warning`, `security`: `History orders at https://repo-graph-port.aoa.run refused the key from 198.51.100.4` |
| — | `box.warning`, `security`: `History orders at https://repo-graph-port.aoa.run blocked Maxitor for too many wrong keys; the last came from 198.51.100.4` |
| uvicorn: `"GET /api/v1/full-graph?source=… HTTP/1.1" 200` | `"GET /api/v1/full-graph" 200` |

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `MAXITOR_PUBLIC_PORT` | none | Maxitor's own port, for public GitHub links only; internal, never shown (research R16). Unset → public links refused |
