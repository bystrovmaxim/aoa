# Phase 1 — Data Model: One shared coordinator graph, declared once

**Feature**: `specs/005-shared-graph-resource` · **Date**: 2026-10-16

This feature stores nothing new. It has a data model only in the sense that three objects and the
states between them must be stated precisely: the **application slot**, the **shared resource**
that reads it, and the **route registration** that hands the resource over. Everything below is
derived from [spec.md](./spec.md) and [research.md](./research.md).

---

## E1. Application slot

The single place a loaded graph lives for the whole application.

| | |
| --- | --- |
| **Lives on** | `fastapi_app.state.duckdb_graph` — the `FastAPI` instance built by `create_app()` |
| **Type when filled** | `DuckDBGraphResource` (`packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py`) |
| **Initialised** | in the lifespan, to `None` (`app.py:67`) |
| **Written by** | `POST /api/load` only (`routes/load.py:42`), and only after both runs succeed |
| **Read by** | the shared resource (E2) on every read; the load path itself, which passes the freshly built graph to the sidebar action by hand |
| **Cardinality** | exactly one per application object; two applications in one process have one each |

**Lifecycle**

```text
                    create_app()            lifespan starts          POST /api/load succeeds
   (no attribute) ───────────────► (no attribute) ──────────► None ──────────────────────► DuckDBGraphResource
                                                                  ▲                                │
                                                                  │      POST /api/load fails      │
                                                                  └────────────────────────────────┤
                                                                                                   │
                                          POST /api/load succeeds again ───────────────────────────┘
                                                     (the previous graph is replaced, unread)
```

**Rules**

- **DM-001**: The slot is written **only** after a load has succeeded end to end, including the
  sidebar run. A load that fails at any point leaves the slot exactly as it was (FR-011).
- **DM-002**: Writing the slot replaces its value for every route at once. Nothing is merged, and
  no caller is notified (FR-011; the isolation defect is [#214](https://github.com/bystrovmaxim/aoa/issues/214)).
- **DM-003**: Reading the slot is a single attribute lookup. A read therefore observes either the
  value from before a load or the value from after it, never a mixture.

---

## E2. Shared graph resource — `DuckDBGraphHolder`

The ready, application-scoped `BaseResource` every diagram route is handed.

| | |
| --- | --- |
| **Module** | `packages/aoa-maxitor/src/aoa/maxitor/api/duckdb_graph_holder.py` (new) |
| **Base** | `aoa.action_machine.resources.base_resource.BaseResource` (directly; see research R2) |
| **Decorator** | `@meta(description=…, domain=DiagramsDomain)` — required by convention, unenforced because `BaseResource` is `@exclude_graph_model` |
| **State** | one field: the `FastAPI` application object it was built for. **No graph reference is ever stored.** |
| **Constructed** | once per `create_app()` call, while the application is being built (FR-002) |
| **Lifetime** | the application object's; never opened, never closed (FR-009) |

**Members**

| Member | Kind | Contract |
| --- | --- | --- |
| `__init__(app)` | method | Stores the application. Nothing is resolved, read or validated here. |
| `get_wrapper_class()` | method | Returns `None` — passthrough when propagated to nested actions (FR-009, research R4). |
| `check_rollup_support()` | async method | Returns `False` — an in-memory read-only store, the same answer `ExternalServiceResource` gives. |
| `service` | property | Resolves the slot, then returns the loaded graph's `.service` (the DuckDB connection). |
| `execute_fetch_dicts(query, parameters=None)` | method | Resolves the slot, then delegates to the loaded graph's own method. |
| `_resolve()` | private method | Reads the slot; raises `HandleError` when there is nothing loaded. |

**Rules**

- **DM-004**: `service` and `execute_fetch_dicts` are the **only** operations. Each resolves the
  slot at the moment of the call; neither caches a graph (FR-005, FR-006).
- **DM-005**: No attribute or call is forwarded to the resolved graph. `__getattr__` is not used.
- **DM-006**: No lifecycle member exists — no `open`, `close`, `begin`, `commit`, `rollback` — and
  none is inherited from `BaseResource` (FR-009).
- **DM-007**: The resource holds a reference to the **application**, not to a module-level global,
  so two applications built in one process resolve their own slots (FR-004).

---

## E3. Read states of `_resolve()`

Three states, and the answer for each. The state is derived from the slot at read time.

| State | Slot | `service` / `execute_fetch_dicts` | Requirement |
| --- | --- | --- | --- |
| **Absent** | the attribute does not exist (the lifespan has not run) | raises `HandleError` | FR-007; clarification "absent and empty are the same answer" |
| **Empty** | `None` | raises `HandleError` | FR-007 |
| **Loaded** | a `DuckDBGraphResource` | returns / delegates to it | FR-005 |

The absent and empty states are deliberately indistinguishable. The read is
`getattr(app.state, "duckdb_graph", None)`, so an application that has been built but not started
answers exactly like one that has started and loaded nothing.

**The failure** (FR-007, FR-008)

- Type: `aoa.action_machine.exceptions.HandleError`, exported from the package `__init__`.
- Message: names the situation — no graph is loaded — and the remedy: call the load endpoint first.
  It must not mention a factory, a return type, or any other framework plumbing.
- It replaces today's `TypeError: PerCallConnection factory for key 'DuckDBGraph' must return
  BaseResource, got 'NoneType'`, which is raised by `resolve_connections`
  (`per_call_connection.py:89-93`) before the action ever runs.
- It is a Python-level failure only. What the caller receives over HTTP is unchanged: no handler is
  registered for it, no status is chosen, no body is shaped (clarification; research R7).

---

## E4. Route registration

The six diagram routes, each declared with the same connection value.

| # | Path (mounted under `/api/v1`) | Action | Connection key | Value today | Value after |
| --- | --- | --- | --- | --- | --- |
| 1 | `/list-domains` | `ListDomainsAction` | `DuckDBGraph` | `PerCallConnection(factory=lambda: fastapi_app.state.duckdb_graph)` | the one `DuckDBGraphHolder` |
| 2 | `/list-entities` | `ListEntitiesAction` | `DuckDBGraph` | same object | same object |
| 3 | `/list-node-types` | `ListNodeTypesAction` | `DuckDBGraph` | same object | same object |
| 4 | `/full-graph` | `FullGraphAction` | `DuckDBGraph` | same object | same object |
| 5 | `/lifecycle-finite-automaton` | `GetLifecycleFiniteAutomatonAction` | `DuckDBGraph` | same object | same object |
| 6 | `/domain-use-case-diagram` | `GetDomainUseCaseDiagramAction` | `DuckDBGraph` | same object | same object |

"Same object" in the *today* column is the point of the feature: the six routes already shared one
`PerCallConnection` **wrapper** whose factory returned one slot, so the sharing was real and the
declaration was the only thing that was wrong. After the change the six routes share one
`DuckDBGraphHolder` **resource**, and the declaration says so.

**Rules**

- **DM-008**: The connection key is `DUCKDB_GRAPH_CONNECTION_KEY` = `"DuckDBGraph"` on both the
  routes (`app.py:47`) and the load path (`load.py:14`). It does not change (FR-010).
- **DM-009**: The actions' own `@connection(DuckDBGraphResource, key=DUCKDB_GRAPH_CONNECTION_KEY)`
  declarations do not change. The declared type is metadata; the supplied value is checked only for
  being a `BaseResource` (research R1).
- **DM-010**: Exactly one `DuckDBGraphHolder` instance per application. It is built before any
  route is registered, so the declaration is complete before the app can be reached.
- **DM-011**: For any loaded graph, each of the six routes returns the JSON it returned before
  (FR-014). No payload, key, ordering or type changes.

---

## E5. What this feature deliberately does not model

- **A second graph, a session, a per-user slot.** [#214](https://github.com/bystrovmaxim/aoa/issues/214).
- **A lifetime for per-call resources, and a mandatory way to close one.**
  [#215](https://github.com/bystrovmaxim/aoa/issues/215). The holder is deliberately outside that
  migration, which is part of why it lands first (spec, Clarifications).
- **A user-visible unloaded state** — in the transport or in the SPA. The caller's experience is
  unchanged by decision (spec, Clarifications).
- **A graph model node for the holder.** `BaseResource` is `@exclude_graph_model`, so the holder
  adds no vertex and no edge to any diagram; the six routes' declared connection metadata is
  unchanged, so no published graph differs.
