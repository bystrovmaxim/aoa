# Contract: graph reads name their source

**Feature**: [../spec.md](../spec.md) · **Research**: [../research.md](../research.md) R1, R2, R6

## Graph reads

Applies to every route under `/api/v1/` and to `GET /api/sidebar`.

```
GET /api/v1/<diagram>?source=<url-encoded graph-json URL>&<the route's own parameters>
GET /api/sidebar?source=<url-encoded graph-json URL>
```

| Situation | Status | Body |
|---|---|---|
| `source` held by the store | as today (200 with the route's payload) | as today |
| `source` not held, builds successfully | as today; the build happens before the answer | as today |
| `source` missing or blank | **400** | `{"detail": "Missing query parameter 'source': name the graph-json URL this read is for."}` |
| `source` cannot be built (unreachable, not a graph, invalid JSON) | **422** | `{"detail": "<the load's reason, as POST /api/load gives it today>"}` — repeated without a new download for 10 s |
| no build slot freed within 30 s | **503**, header `Retry-After: 5` | `{"detail": "Maxitor is busy building other graphs; try again shortly."}` — not remembered: the next read builds again |

Rules:

- One request is answered from one graph, whatever happens to the store while it runs.
- The route's own parameters, and its answers, do not change.
- `GET /api/sidebar` no longer answers an empty payload for "nothing loaded": a read without a source is a 400 like every other graph read.
- `GET /api/health` and the static files do not take `source`.
- Refusals (400, 422, 503) carry the same CORS headers as successful answers; `OPTIONS` requests pass through untouched. The 503 also sends `Access-Control-Expose-Headers: Retry-After`, so a client on another origin can read the pause (`Retry-After` is not a CORS-safelisted response header).
- The source is sent URL-encoded (`URLSearchParams`); an address containing `&`, `+`, `%2F` or a space reaches the store as the same key it has in `POST /api/load`. A literal `+` travels as `%2B`: an unencoded `+` is read as a space and names a different source.

## `POST /api/load` — rebuild one source

```
POST /api/load
{"service_url": "<graph-json URL>"}
```

| Situation | Status | Body | Store |
|---|---|---|---|
| build succeeds | 200 | `{"status": "ok"}` | the source's entry is replaced (or inserted) |
| build fails | 422 | `{"detail": "<reason>"}` | the previous entry of that source, if any, stays |
| no build slot freed within 30 s | **503**, header `Retry-After: 5` | `{"detail": "Maxitor is busy building other graphs; try again shortly."}` | the previous entry of that source, if any, stays |

No other source is touched in either case.

## `GET /api/health`

```json
{"status": "ok", "graphs_held": 3, "builds_running": 4, "builds_queued": 2}
```

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `MAXITOR_MAX_GRAPHS` | `50` | most graphs one process holds; beyond it the least recently read one is removed |
| `MAXITOR_GRAPH_IDLE_SECONDS` | `300` | a graph unread this long is removed |
| `MAXITOR_MAX_CONCURRENT_BUILDS` | `4` | builds running at once across all sources; the rest wait for a slot, up to 30 s |

## Browser behaviour (the client's side of the contract)

| User action | Requests sent |
|---|---|
| opens `/?source=<url>&view=<view>` | graph reads with `source=<url>`; **no** `POST /api/load` |
| submits a source in "AOA Service URL" | one `POST /api/load`, then graph reads |
| clicks "Reload from service" | one `POST /api/load` for the current source, then `GET /api/sidebar` and the current diagram's read |
| leaves the source | nothing |
| deep link, server busy (503) | the source and the diagram stay on screen with a "busy, retrying" message; the read is retried after `Retry-After`, then after 10 s, 20 s and at most 30 s between later tries; **no** prompt and **no** `POST /api/load` |
| start page, no source | nothing graph-related |

A `POST /api/load` answered with 503 is shown on the button and is **not** retried automatically: the user decides when to try again. Only reads keep the automatic retry of FR-029, and one page keeps one retry loop.

The deep-link format `?source=…&view=…` is unchanged.
