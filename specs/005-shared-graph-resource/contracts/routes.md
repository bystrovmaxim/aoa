# Contract: what the six diagram routes answer

**Feature**: `specs/005-shared-graph-resource` · **Date**: 2026-10-16

The feature changes how the six routes are **declared**, not what they **answer**. This contract
fixes both halves so that a reviewer can tell a correct change from a regression, and so that the
"unchanged" claim is checkable rather than asserted.

---

## 1. The routes

Mounted at `/api/v1` on the sub-application built by `FastApiAdapter.build()`
(`packages/aoa-maxitor/src/aoa/maxitor/api/app.py:98-123`).

| Path | Action |
| --- | --- |
| `GET /api/v1/list-domains` | `ListDomainsAction` |
| `GET /api/v1/list-entities` | `ListEntitiesAction` |
| `GET /api/v1/list-node-types` | `ListNodeTypesAction` |
| `GET /api/v1/full-graph` | `FullGraphAction` |
| `GET /api/v1/lifecycle-finite-automaton` | `GetLifecycleFiniteAutomatonAction` |
| `GET /api/v1/domain-use-case-diagram` | `GetDomainUseCaseDiagramAction` |

Every one of them declares the same connection:
`connections={DUCKDB_GRAPH_CONNECTION_KEY: <the one shared resource>}`.

- **R-1.1** Six routes, six declarations, **one** connection value shared by all of them.
- **R-1.2** The key is `DUCKDB_GRAPH_CONNECTION_KEY` = `"DuckDBGraph"`, on the routes and on the
  load path alike.
- **R-1.3** The actions' own `@connection(DuckDBGraphResource, key=…)` declarations are untouched.

## 2. With a graph loaded

- **R-2.1** Each route answers `200` with **exactly** the JSON it answered before this feature, for
  the same graph: same keys, same nesting, same ordering, same types, same values.
- **R-2.2** Each route reads the graph through the shared resource; the connection it receives is a
  `BaseResource` the framework accepts for the declared key.
- **R-2.3** Two consecutive requests — to the same route or to two different routes — read **one and
  the same** graph object. The sharing is across requests, not merely across routes.
- **R-2.4** After `POST /api/load` succeeds again, every route reads the **newly** loaded graph.
  Nothing answers from the previous one.

## 3. With nothing loaded

Measured on the current application, not assumed. The adapter's `_CatchAllErrorsMiddleware`
(`packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py:527-550`) wraps every request in
`try/except Exception` and answers `500 {"detail": "Internal server error"}` **without logging what
it caught**. No uncaught exception therefore reaches a caller, a log or a test that drives the app.

- **R-3.1** Reading the shared resource raises `HandleError`, whose message names the situation and
  the remedy: no graph is loaded, call the load endpoint first. This is readable where the resource
  is driven directly — a test, a debugger, a script — and nowhere else.
- **R-3.2** No read raises `TypeError`, and none reports that a per-call factory returned `NoneType`.
- **R-3.3** The response a caller receives over HTTP is **unchanged from before this feature**, in
  status and in body. No exception handler, status or response body is added for this failure; the
  adapter's existing catch-all is what produces the answer, and it produces the same one either way.
- **R-3.4** The two routes that require a query parameter (`/lifecycle-finite-automaton`,
  `/domain-use-case-diagram`) answer `422` with the missing-parameter detail before the connection is
  touched, both before and after this feature.
- **R-3.5** A read that arrives before the application's lifespan has run raises the same
  `HandleError`, not an `AttributeError`.

## 4. The neighbouring routes, which this feature does not touch

| Path | Behaviour |
| --- | --- |
| `POST /api/load` | builds the graph, runs the sidebar against the freshly built graph, then writes the slot. Returns `{"status": "ok"}`, or `422` with the failure text. Unchanged. |
| `GET /api/health` | `{"status": "ok"}`. Unchanged. |
| the sidebar route | unchanged, including the case where the load path passes the freshly built graph by hand rather than through the holder. |

- **R-4.1** A load that fails — unreachable service, malformed payload, or a failing sidebar run —
  returns `422` and leaves the slot exactly as it was. A graph loaded successfully earlier is still
  the one every route reads.
- **R-4.2** `POST /api/load` remains the only writer of the slot.

## 5. How this contract is checked

| Clause | Instrument |
| --- | --- |
| R-1.1 | counting real `DuckDBGraphHolder` constructions during the real `create_app()` — exactly one per call. Reading the registrations back is **impossible**: the adapter that holds them is discarded and the endpoints close over them, see [research.md](./research.md) R10 |
| R-1.2 | the connection key is read from the source of `app.py` and `routes/load.py`, and asserted equal |
| R-1.3 | the actions' declarations are read from source and asserted unchanged |
| R-2.1 | the existing per-action tests, unchanged, plus a route-level test through the app |
| R-2.2 | a route-level test through the app — a wrong connection value fails validation before the first aspect |
| R-2.3 | the holder read twice against a recording stand-in (research R5), together with R-1.1's single construction |
| R-2.4 | a route-level test that replaces the slot and asserts **every** of the six routes answers from the new one |
| R-3.1, R-3.2, R-3.5 | the resource is read directly and the raised `HandleError` is asserted — `TestClient` cannot be used, because the adapter catches first (research R8) |
| R-3.3, R-3.4 | `TestClient` with `raise_server_exceptions=False` over all six routes, asserting the status and body match today's measured baseline |
| R-4.1, R-4.2 | the existing load tests, unchanged, plus a route-level test after a failed load |

No clause of this contract is checked by a mock that stands in for the framework. Every clause is
checked against the running application or against the object the routes actually use. The one
piece of instrumentation — wrapping `DuckDBGraphHolder` to count its real constructions — observes
the application rather than replacing it: the class still does its work, and only the fact that it
was constructed is recorded.
