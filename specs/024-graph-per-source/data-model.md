# Data Model: One Graph per Source

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

## Source

The `graph-json` URL exactly as the user gave it (`?source=` in the browser, `source` on every read, `service_url` in `POST /api/load`). It is the store's key. No normalization: `https://a/graph-json` and `https://a/graph-json/` are two keys.

## GraphEntry

One build of one source.

| Field | Meaning |
|---|---|
| `source` | the key it was built for |
| `graph` | the `DuckDBGraphResource` the diagram actions query |
| `sidebar` | the `GetLeftMenuSidebarDataAction` result built from that same graph |
| `last_read` | monotonic time of the latest acquire; drives idle removal and least-recently-read eviction |

Invariants: `graph` and `sidebar` come from the same build (FR-002); an entry is never mutated after it is built, except `last_read`.

## GraphStore

| Field | Meaning |
|---|---|
| `entries` | `source → GraphEntry`, ordered by `last_read` |
| `in_flight` | `source → future` of the one build running for it, from `acquire` or `reload` |
| `failures` | `source → (reason, time)` of the last failed build, kept 10 s |
| `max_graphs` | capacity, default 50 (`MAXITOR_MAX_GRAPHS`); a positive integer, otherwise the app refuses to start naming the variable |
| `idle_seconds` | idle timeout, default 300 (`MAXITOR_GRAPH_IDLE_SECONDS`); a positive number, otherwise the app refuses to start naming the variable |
| `max_concurrent_builds` | builds running at once across all sources, default 4 (`MAXITOR_MAX_CONCURRENT_BUILDS`); a positive integer, otherwise the app refuses to start naming the variable |
| `clock` | monotonic clock, injected for tests |
| `builder` | `async (source) → GraphEntry`, runs the two load actions (research R5) |

Operations:

| Operation | Behaviour |
|---|---|
| `acquire(source)` | sweep idle entries; if held → update `last_read`, return it; if building → await that build; else start one build, await it, store it (evicting the least recently read entry beyond `max_graphs`), return it. A failed build raises `GraphBuildError(reason)` to every waiter and stores nothing. The build runs as its own task, and waiters await it shielded: a waiter that is cancelled (its reader left) stops waiting, but the build goes on for the others and its entry is stored. |
| `reload(source)` | build a fresh entry; on success replace the held one (or insert); on failure keep the held one and raise `GraphBuildError`. |
| `sweep()` | remove every entry whose `last_read` is older than `idle_seconds`, and every `failures` record older than 10 s. |
| `held` / `building` / `queued` | entries held, builds running, builds waiting for a slot; reported by `GET /api/health`. |

Every build, from `acquire` or `reload`, runs inside the `max_concurrent_builds` bound; a build that waits 30 s for a slot fails with `GraphStoreBusyError` (answered as 503). The slot is taken inside the build task, never before it, and after any wait on `in_flight`: a caller that holds a slot while waiting for another build to finish would deadlock once enough callers do it. A failed build is remembered for 10 s in `failures`; `acquire` within that window raises the same `GraphBuildError` without building; `reload` ignores it. Only `GraphBuildError` is recorded there: `GraphStoreBusyError` is never remembered, because "no slot" says nothing about the source.

One build in flight per source, of any kind: `reload` that finds `in_flight[source]` awaits it, then starts its own build, so the stored entry is always the reload's.

## Lifecycle of an entry

```text
            acquire (cold)                 acquire (held)
 (absent) ───────────────► building ─────► held ◄────────────┐
    ▲                         │  fail        │ │              │
    │                         └──────────────┘ │ reload ok ───┘ (replaced by a new entry)
    │   idle_seconds without a read            │
    ├──────────────────────────────────────────┤
    │   evicted: least recently read, store full
    └──────────────────────────────────────────┘
```

Removal or replacement drops only the store's reference; a request holding the entry finishes on it (FR-006, research R4).

## Request binding

For one HTTP request to `/api/v1/*` or `/api/sidebar`, the middleware binds the acquired `GraphEntry` to a context variable before the endpoint runs and resets it after the response. `DuckDBGraphHolder._resolve()` and the sidebar route read that variable; outside a bound request the holder raises `HandleError` naming the missing binding. One request sees one entry (FR-007).
