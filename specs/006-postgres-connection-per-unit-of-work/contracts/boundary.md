# Contract: the boundary

**Feature**: `specs/006-postgres-connection-per-unit-of-work` · **Date**: 2026-10-16

The boundary is the one place the per-call lifecycle is applied. It is the adapters, at the points
where they resolve connections before running the machine (spec, Assumptions). Nothing below is
database-specific: the boundary knows a factory, a finalizer and a context manager, and no driver.

---

## 1. The four call sites

| # | File | Function | Today | After |
| --- | --- | --- | --- | --- |
| 1 | `packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py` | `_make_endpoint_with_body` (def `:259`) | `resolve_connections(record.connections)` at `:299`, then `machine.run` at `:302` | `async with connection_scope(record.connections) as connections:` around the run |
| 2 | same | `_make_endpoint_with_query` (def `:324`) | resolve at `:369`, run at `:372` | same |
| 3 | same | `_make_endpoint_no_params` (def `:426`) | resolve at `:468`, run at `:471` | same |
| 4 | `packages/aoa-mcp-adapter/src/aoa/mcp/adapter.py` | `_execute_tool_call` (def `:382`), called from `_make_tool_handler` (`:307`) | resolve at `:407`, run at `:410` | the scope is applied **inside `_execute_tool_call`**, which already holds `record`, around its `machine.run` |

- **B-1.1** These are the four places that resolve connections before a run, and the only ones the
  lifecycle is installed at (FR-038; spec Clarification).
- **B-1.2** The resolved mapping is produced **by** the scope, not before it: the scope resolves,
  opens, yields and finalizes. A resolve followed by a bare `machine.run` would leave the resources
  unopened and unfinalized (FR-016, FR-017).
- **B-1.3** The MCP resolve sits inside `_execute_tool_call`, not in `_make_tool_handler`: the scope is
  applied where the machine is actually run, so no signature has to change — `_execute_tool_call`
  already receives `record`. The handler's `try/except` that builds the JSON envelope stays outside,
  and the envelope shape is unchanged.
- **B-1.4** The machine still receives only `dict[str, BaseResource] | None` (FR-022).

**Note on the site names** — the empty-parameter endpoint is `_make_endpoint_no_params` (def `:426`),
not `_make_endpoint`; `_make_endpoint` (`:487`) is the dispatcher that chooses among the three
factories. The design brief named the dispatcher, the code names the builder. Both refer to the same
site; this contract follows the code. The three FastAPI definitions are cited by their `def` lines
(`:259`, `:324`, `:426`); the resolve lines inside them are `:299`, `:369`, `:468`.


## 2. The adapter's lifecycle option (FR-038)

Each adapter gains exactly one option, **keyword-only, default `None`**: an asynchronous context
manager run at startup and closed at shutdown.

- **B-2.1** `FastApiAdapter.build(lifespan=None)` — the option is on the builder, not the
  constructor, because the application is created in `build()` (`adapter.py:802`). It is installed by
  wrapping the `FastAPI(lifespan=...)` argument at `adapter.py:816-820`: when the option is `None`
  the argument is not added; otherwise it is passed through.
- **B-2.2** `McpAdapter.build(lifespan=None)` — `adapter.py:555-558` becomes
  `FastMCP(self._server_name, tools=tools, lifespan=lifespan)`. Measured:
  `mcp.server.fastmcp.FastMCP.__init__` accepts `lifespan`, and there is no `run_async` method
  (binding decision).
- **B-2.3** Nothing database-specific appears in the adapter: no pool, no connection, no driver
  name. An application hangs its pool's creation and closure inside the context manager
  (FR-038, SC-021).
- **B-2.4** Exactly one such option exists per adapter; it is not a registry and not a hook list
  (SC-021).
- **B-2.5** The option is what makes the pool reachable through the application's own holder, since
  the action never receives the pool (FR-012).

**The bound and the order (FR-038)** — settled in the design, and stated here so the implementation
does not have to invent it. The adapter adds **no bound of its own and no ordering of its own**: the
context manager's closing is the framework's own startup/shutdown contract, because the adapter does
nothing but hand the hook to the framework that owns it (`FastAPI(lifespan=…)`; `FastMCP(…,
lifespan=…)`). What the adapter owes under FR-038 is the statement, in its documentation, that the
hook runs when the application or server starts and stops, and that how long its closing takes and
where it sits relative to the server's own shutdown are the framework's to define. Inventing a
timeout here would be the adapter pretending to own a lifecycle it merely forwards.

## 3. The pool is never a connection

- **B-3.1** The pool is process state and never enters an action's `connections`; the action does not
  use it (FR-012).
- **B-3.2** It reaches the routes through the application's own holder; reading the holder before it
  is filled is a named failure (FR-013).
- **B-3.3** The boundary never opens, closes or inspects the pool. Only the finalizer touches it, and
  only to `release` a borrowed connection (FR-006, FR-007).
- **B-3.4** A resource declared with its own connection parameters uses its own connection; the pool
  is never touched by that call (FR-005, FR-007).

## 4. What the boundary must NOT do

- **B-4.1** It must not open or close a resource that was supplied ready; that resource's lifetime
  belongs to whoever supplied it (FR-019).
- **B-4.2** It must not close the pool, at request time or at shutdown beyond handing the context
  manager scope to the application (FR-007, FR-008).
- **B-4.3** It must not use a database-specific name — no `pool`, `dsn`, `connection`, `asyncpg`,
  `Postgres` — in the adapter's new option or its wrapping code (FR-038, SC-021).
- **B-4.4** It must not let a closing failure replace the run's failure (FR-020).
- **B-4.5** It must not change the mapping shape the machine receives (FR-022).
- **B-4.6** It must not finalize an entry twice, and must finalize the opened ones on the path where
  a later `open()` has already failed (FR-017, FR-021).
