# Research: One Graph per Source, Named by Every Request

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Date**: 2026-10-26

## Measurements taken for this plan

Against the reference source `https://admingameoffer.aoa.run/graph-json`, from the maintainer's machine, with the repository's environment (`uv run`), using `DuckDBGraphResource.build_from_json` directly:

| Measure | Value |
|---|---|
| `graph-json` body | 306 754 B |
| download from this machine | 5.4 s (network-bound; the stand measured 1.6 s for the whole `POST /api/load`) |
| DuckDB build, first in a process | 0.605 s |
| DuckDB build, later ones | 0.127–0.144 s |
| memory of one built graph (`duckdb_memory()`) | **47.9 MiB**, of which `ART_INDEX` 37.8 MiB, `IN_MEMORY_TABLE` 6.9 MiB, `BASE_TABLE` 3.0 MiB |
| process RSS growth per extra graph | ≈ 50–58 MiB |

Process RSS while holding graphs (macOS): 75 MiB with none, 191 MiB with 1, 400 MiB with 5, 665 MiB with 10; **663 MiB after dropping all 10** and collecting; 669 MiB with 3 built again. Memory is taken per built graph and reused after a drop, but not returned to the system. The Linux behaviour, and whether the indexes are needed at all, are #268.

Consequence for FR-004: the clarified default of **50 graphs is about 2.4 GiB** in the worst case, almost all of it primary-key indexes. A graph read by a burst of readers on one link is one graph (48 MiB); the worst case needs 50 different sources within the idle timeout. The limit stays configurable (R3). Shown these numbers, the maintainer kept 50, on the condition, confirmed above, that memory is taken per built graph and not reserved up front.

## R1 — How a read names its source

- **Decision**: a query parameter `source` on every graph read: `GET /api/v1/<diagram>?source=<url>&…` and `GET /api/sidebar?source=<url>`.
- **Rationale**: the browser already holds the source as `?source=` in its own URL; a query parameter makes every answer addressable by URL, so HTTP caching (#245) can key on it without `Vary`. A custom header would make every cross-origin read a CORS preflight (the app allows any origin) and double the requests.
- **Alternatives considered**: a custom header (`X-AOA-Source`) — rejected for the preflight and `Vary` cost; a field in every action's `Params` — rejected because the source selects the *resource*, not an input of the action, and six action schemas would change for a concern none of them reads.

## R2 — Where the source is turned into a graph

- **Decision**: a pure ASGI middleware on the main application, applied to `/api/v1/` and `/api/sidebar`. It reads `source`, answers **400** when it is missing, acquires the graph from the store (building it when cold), answers **422** with the build's reason when it cannot be built, and otherwise binds the acquired entry to a context variable for the rest of that request. `DuckDBGraphHolder` stays a ready resource (mode 1) and resolves the request's bound entry instead of `app.state`.
- **Rationale**:
  - `PerCallConnection.factory` takes no arguments (`per_call_connection.py`), so nothing inside the adapter can see the request's query string.
  - A failure raised inside an action reaches the caller as the adapter's generic `500 {"detail":"Internal server error"}` (shown by `examples/step_26_maxitor/02_api_shared_graph.py`, step 1). FR-010 and FR-011 need a named reason, so the answer must be given before the adapter runs.
  - Binding the entry once per request gives FR-007 for free: every `_resolve()` inside one request returns the same entry, whatever the store does meanwhile.
  - A pure ASGI middleware sets the context variable in the same task that runs the endpoint; `BaseHTTPMiddleware` runs `call_next` in a separate task and is avoided.
  - **Order against CORS**: the middleware is installed **inside** `CORSMiddleware` (added before it, since Starlette's last-added middleware is the outermost), so its 400, 422 and 503 carry `Access-Control-Allow-Origin` like any answer, and `OPTIONS` requests pass through it untouched. The 503 must also expose `Retry-After`: it is not a CORS-safelisted response header, so without `Access-Control-Expose-Headers` a client on another origin cannot read it and would retry on its own guess. On the stand and in development the client is same-origin (FastAPI serves the SPA; Vite proxies `/api`), so this matters when the client is built with `VITE_MAXITOR_API_BASE_URL` pointing elsewhere — exactly the case where the client's 422 fallback (FR-023) would otherwise see a network error.
  - **One key from both paths**: Starlette decodes the query string and the load route reads the JSON body, so the same address arrives as the same string as long as the client encodes it with `URLSearchParams`/`encodeURIComponent`. An unencoded `+` in a query string is read as a space (`parse_qsl('source=https://x/a+b')` gives `https://x/a b`), so a literal `+` must travel as `%2B`. A test sends an address containing `&`, `+`, `%2F` and a space through both paths and asserts one key.
- **Alternatives considered**: a per-call factory reading a context variable — still needs the middleware to set it, and adds a lifecycle the holder does not have; resolving inside each action — rejected for the 500 above.

## R3 — The graph store

- **Decision**: an in-process `GraphStore` owned by the application: `source → entry(graph, sidebar, last_read)`.
  - **Single flight**: one in-flight build per source (an `asyncio` future); concurrent acquirers await it, so a burst costs one download and one build (FR-003, FR-013). A failed build fails every waiter with the same reason and stores nothing (FR-011).
  - **Idle removal**: an entry unread for `idle_seconds` (default 3600) is removed. The sweep runs on every store access, so no background task exists; an idle process keeps its last graphs until the next request, which is acceptable because nothing competes for that memory meanwhile.
  - **Capacity**: at most `max_graphs` (default 50); inserting beyond it removes the least recently read entry.
  - **Configuration**: environment variables `MAXITOR_MAX_GRAPHS` and `MAXITOR_GRAPH_IDLE_SECONDS`, read where the app is built, as `MAXITOR_API_HOST` / `MAXITOR_API_PORT` already are.
  - **Clock**: injected (`time.monotonic` by default) so tests can move time without sleeping.
  - **A bound on builds across sources**: an `asyncio.Semaphore` of `max_concurrent_builds` (default 4, `MAXITOR_MAX_CONCURRENT_BUILDS`) wraps every build. Single flight alone bounds builds per source, not across sources: 300 different cold sources would otherwise build 300 graphs at once, about 15 GiB before the capacity limit acts, since eviction happens only after a build is stored. Refusing with 503 instead of waiting was rejected: the reader would only retry, and waiting already bounds memory. The order in which waiting builds get a slot is not promised.
  - **What the bound costs, and the two guards**: a download has a 15-second timeout (`load_aoa_service_action.py:152`), so four unreachable addresses can hold all four slots for 15 seconds, and every cold read of every source waits behind them. Two guards limit this: a failed source is remembered for 10 seconds (reads in that window get the same 422 without downloading; an explicit reload ignores the memory; a busy refusal is never remembered, or a good source would answer "bad source" for 10 s after a moment of congestion), and a read that waits 30 seconds for a slot gets a 503 instead of hanging. Many distinct bad addresses can still fill the slots; accepted consciously, because the real fix is the allowlist, which is out of scope.
  - **One build in flight per source, of any kind**: `acquire` and `reload` share `in_flight`. A reload that finds a build running for its source awaits it and then starts its own; so the reload's graph is the one stored last, and a slower earlier build can never overwrite a fresh one. The build takes its slot **after** that wait, never before: a reload that held a slot while waiting for a build which itself waits for a slot would deadlock as soon as four of them did it.
  - **Counters for operators**: the store exposes `held` (graphs held), `building` (builds running) and `queued` (builds waiting for a slot); `GET /api/health` reports all three, so a full queue is visible as such.
  - **A leaving reader does not cancel the build**: the build is its own `asyncio` task and every waiter awaits it through `asyncio.shield`. Otherwise the first reader of a burst who closes the tab would cancel the build every other reader is waiting for.
  - **Where the middleware finds the store**: at request time, from `scope["app"].state.graph_store`. Tests replace `app.state.graph_store` with a store over a stub builder; `create_app()` gains no parameter for tests.
- **Rationale**: the smallest structure that meets FR-001–FR-006; one process, one event loop, so no thread locks.
- **Alternatives considered**: `functools.lru_cache` / `cachetools` — neither gives single-flight async builds or idle removal; an external store — out of scope.

## R4 — Removal never closes a graph by force

- **Decision**: removing or replacing an entry only drops the store's reference. A request that acquired it holds its own reference through the context variable; CPython frees the DuckDB connection when the last reference goes.
- **Rationale**: FR-006 without reference counting of our own; `DuckDBGraphResource` is never closed explicitly today either.
- **Alternatives considered**: explicit `close()` with pin counts — more code for the same outcome.

## R5 — What a build is

- **Decision**: the store's builder runs the two actions `POST /api/load` runs today, `LoadAOAServiceAction` then `GetLeftMenuSidebarDataAction`, through the application's machine, and keeps both results as one entry (FR-002).
- **Rationale**: no second loading path; the download timeout and error messages stay as they are (spec Assumptions).
- **Not done here**: moving the 0.13–0.6 s DuckDB build off the event loop. It runs once per source; during it other requests wait. Recorded as a known limit, not addressed by this feature.

## R6 — `POST /api/load`

- **Decision**: it becomes `store.reload(source)`: download and build a fresh entry, replace the old one on success, keep the old one and answer 422 with the reason on failure (FR-014, FR-015). The request and response shapes do not change (`{"service_url": …}` → `{"status": "ok"}`).

## R7 — The client

- **Decision**:
  - `client/src/api/client.ts` gains an active source (`setActiveSource`) and `graphApiUrl(path, query?)`, which appends `source` to every graph read and throws when no source is active. Every graph read uses it; `loadGraph` keeps its body.
  - **Deep link**: set the active source and read — no `loadGraph`. The sidebar read is the probe: a 422 sends the page to the manual "AOA Service URL" prompt, as today (FR-017, FR-023); a 503 does not — it keeps the source, shows that Maxitor is busy and retries, because the source itself is good (FR-029). The page keeps one retry loop however many reads it holds, so one busy source does not multiply the queue it waits for. The retry honours the server's `Retry-After: 5` and doubles the pause after each further 503, up to 30 s, so a crowd of busy clients does not lengthen the queue it is waiting for.
  - **Typed source**: `loadGraph` once, then read (FR-018).
  - **Leaving**: clear the active source and the browser state; nothing is sent (FR-019).
  - **"Reload from service"**: `loadGraph(current)` once, then fetch the sidebar again and remount the diagram workspace (a reload counter in its `key`), keeping URL and selection; disabled while running; a failure is shown and the diagram stays (FR-020). A 503 is one of those failures and is not retried: the user asks again when they choose.
  - `useSidebarPayload` stops fetching on mount when no source is active (the start page asks the server for nothing graph-related).
  - **The source is set during the first render**, where `App` already reads the deep link into `initialLinkRef`, not in an effect: `useSidebarPayload`'s mount effect is declared before `App`'s deep-link effect and runs first, so a source set in an effect would arrive too late and the sidebar would never be asked for.
  - The active source is module state of the client on purpose: one tab shows one source, so "the current source of this tab" is the intended meaning, unlike the server, where one slot mixed different users. Passing it through every diagram loader would carry the same value with more code.
- **Testing**: the client has no test runner today. Add `vitest` with `jsdom` and `@testing-library/react` as dev dependencies, an `npm test` script, and a check-run step after the build. Tests: the helper appends the source and refuses without one; a deep link sends no `POST /api/load`; a typed source sends one; the button sends one for the current source and then refetches.
- **Alternatives considered**: browser-only verification — kept as the quickstart's end-to-end proof, but not enough on its own: the repository's adversarial rule needs a test that fails when the behaviour is broken.

## R8 — Documentation and examples

- **Decision**: rewrite `examples/step_26_maxitor/02_api_shared_graph.py` and its notebook as `02_api_graph_per_source.py` / `.ipynb`, showing every case: two sources side by side, a cold read, a missing source (400), a source that cannot be built (422), an explicit reload, idle removal and rebuild, capacity eviction, one build for a burst. Update `docs/tutorials/step-26-maxitor.md` (and its `.ru_draft.md`) where it describes loading and the shared graph, and every reference to the old example name.
