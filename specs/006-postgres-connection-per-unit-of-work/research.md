# Phase 0 — Research: One connection per unit of work, and one pool for the process

**Feature**: `specs/006-postgres-connection-per-unit-of-work` · **Date**: 2026-10-16

Every decision below was made against the code in this repository, not against the issue's
sketch. Where the sketch and the code disagree, the code won and the deviation is named.

---

## R1. Is the defect in the code as the issue states it, and what exactly changes?

**Decision**: yes, and the fix is one connection per unit of work, exactly as specified. The
offending line is `postgres_resource.py:84` — `self._conn = await asyncpg.connect(**self._connection_params)`
in `open()` — and every later method of the class uses that one `self._conn`
(`begin()` at :98 executes `BEGIN`, `commit()` at :118 executes `COMMIT`, `execute()` is defined at :136). One resource instance is
therefore one shared session, and two coroutines that reach the same instance collide.

**Rationale**: measured, not inferred. `packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py`
holds exactly one connection field; there is no pool in the package
(`grep -rn "create_pool\|Pool" packages/*/src` returns nothing outside docstrings); and the
per-call path creates **one resource per call** through `PerCallConnection.factory`
(`per_call_connection.py:82`), which means the collision needs either a ready resource shared
between requests or a factory that returns the same object — Maxitor's shape before
[#213](https://github.com/bystrovmaxim/aoa/issues/213). Both are real, and both are cured by the
same change: the resource holds its connection only for its own unit of work.

**Alternatives considered**:
- *A lock around the shared connection* — rejected: it serializes every request, turns the resource
  into a bottleneck, and does nothing about the transaction-interleaving half of the defect,
  because `BEGIN`/`COMMIT` on a shared connection interleave whether or not the statements are
  serialized.
- *One connection per process but per-operation sessions* — rejected: it keeps the connection as
  process state and merely renames the problem; the issue's own invariant is that a resource
  equals a unit of work.

---

## R2. What exactly does `PerCallConnection` become, and does the signature change break callers?

**Decision**: it stays a frozen dataclass and gains a second mandatory field; the field order is
`factory, finalize`.

```python
@dataclass(frozen=True)
class PerCallConnection:
    factory: Callable[[], BaseResource]
    finalize: Callable[[BaseResource], Awaitable[None] | None]
```

**Rationale**: the field order matters and is measured. Today's call sites are a mix of positional
and keyword: three **positional** one-argument sites — `PerCallConnection(factory)` at
`test_fastapi_endpoints.py:200` and `test_resolve_connections.py:37`, and
`PerCallConnection(lambda: "bad")` at `:56` — and three **keyword** ones —
`PerCallConnection(factory=123)` at `test_resolve_connections.py:88`,
`PerCallConnection(factory=factory)` at `test_mcp_handler.py:756`, and
`PerCallConnection(factory=factory)` at `examples/step_17_connections/01_connections.py:96`.
Putting `finalize` second keeps the keyword call sites compiling (they fail only on the missing
mandatory argument, which is the point) and makes the positional ones fail with an ordinary
missing-argument `TypeError` at construction, not at call time. `frozen=True` stays: the declaration
is a value, and the repository's only mutability there would be accidental.

**`validate_connection_entries`** gains the callable check on `finalize`, next to the existing
`factory` check (`per_call_connection.py:51-52`). It still does **not** call either callable.

**`resolve_connections` keeps its signature and its return type.** It is public — imported by
`aoa-fastapi-adapter/src/aoa/fastapi/adapter.py:135` and by the MCP adapter — and five existing
tests call it directly (`test_resolve_connections.py:16, 20, 25, 38, 39, 56`, six call lines).
Changing it to return resources *plus* finalizers would break all of them for no gain: the lifecycle
is applied by a new context manager that walks the declaration itself (R3), and the flat function
stays for the callers that want only the mapping.

**Alternatives considered**:
- *Make `finalize` optional with a `None` default* — rejected: the issue's whole point is that being
  mandatory is what stops a resource being declared without a way to close it.
- *Return a richer object from `resolve_connections` and let the adapter unpack it* — rejected: it
  widens a public function's contract and breaks four tests to save one new module.
- *Let `finalize` default to `resource.close`* — rejected: it would silently bind every declaration
  to one closing convention and make the second parameter ceremonial.

---

## R3. Where does the new lifecycle live, and what is its exact algorithm?

**Decision**: a new module `resources/connection_scope.py` in `aoa-action-machine`, exporting one
async context manager:

```python
@asynccontextmanager
async def connection_scope(
    connections: Mapping[str, ConnectionValue] | None,
) -> AsyncIterator[dict[str, BaseResource] | None]:
```

Behaviour, in order. The scope **walks the declaration itself, entry by entry** — it does not call
`resolve_connections`, because it must know per entry whether the framework created the resource and
must not lose the ones created before a later failure:

1. For each entry, in declaration order: a ready `BaseResource` goes into the yielded mapping
   untouched and is never opened or closed (FR-019); a `PerCallConnection` has its `factory()` called
   now, is recorded as created together with its `finalize`, and is opened with `await resource.open()`
   if it has an `open` attribute (FR-016, FR-018). A `factory()` that raises ends the walk, and the
   entries already recorded are finalized in step 3 (FR-021).
2. Yield the mapping — ready and created resources together — which is exactly what `machine.run`
   receives, unchanged in shape (FR-022).
3. In a `finally`, finalize every created entry exactly once: the opened ones first, then the ones
   whose `open` was never reached or failed, each group in declaration order (FR-017, FR-021). Await
   the result when it is awaitable, so a synchronous finalizer is legal (FR-015). Every remaining
   finalizer still runs after one raises.

**Where it lives, and why**: `aoa-action-machine` is the only package both adapters may depend on,
and this is lifecycle over the resource contract that package owns. It sits beside
`per_call_connection.py` because it consumes the same `ConnectionValue` mapping. It imports no
adapter and no driver, so the package-boundary rules (`scripts/package_boundaries.toml`) are
untouched — `action_machine` has `may_import = []` and this adds no import.

**The error precedence rule, stated exactly** (FR-020, SC-009):

| What the run does | What `finalize` does | What the caller sees |
|---|---|---|
| returns | returns | the run's result |
| returns | raises | the finalizer's error — a leaked connection is never reported as success |
| raises | returns | the run's error, unchanged |
| raises | raises | the run's error; the finalizer's error is appended to it with `add_note` |

**"Recorded" is a mechanism, not an intention**: when the run's error is propagating and a finalizer
also fails, the closing failure is attached to the propagating exception with
`BaseException.add_note` (Python 3.12), so the traceback carries it and the raised exception is still
the run's (FR-020).

**Cancellation** (FR-017, SC-008): finalization runs in the `finally`, so it is reached when the task
is cancelled. A pending cancellation re-raises at the first suspension, so each finalize await is
shielded (`asyncio.shield`) and the `CancelledError` is re-raised after the release completes.

**What is deliberately not done**: a resource that fails to open does not stop the finalization of
the resources already opened (FR-021). A declaration whose resource has no `open` is not opened
(FR-018) but is still finalized. The mapping handed to `machine.run` is the plain
`dict[str, BaseResource]` (FR-022) — the finalizers travel alongside, in the scope's own frame, not
inside the run.


**Alternatives considered**:
- *A `Database`-style object that owns the connection* — rejected: it moves ownership away from the
  resource, which is what the issue fixes; and #216 already owns the query-surface rework.
- *Put the logic in each adapter* — rejected: two copies of an error-precedence rule is one copy too
  many, and the MCP adapter's handler is a different shape from FastAPI's endpoint.
- *An `ExitStack` of `AsyncExitStack`* — rejected on inspection: `finally`-based finalization with an
  explicit exception capture is shorter and makes the masking rule visible, which is the one part a
  reader must not get wrong.

---

## R4. What is the resource's constructor and its lifecycle, precisely?

**Decision**:

```python
class PostgresResource(SqlResource):
    acquire_timeout: float | None = 30.0   # class attribute, not a constructor parameter

    def __init__(self, connection_params: dict[str, Any] | None = None, *,
                 pool: PoolProtocol | None = None, rollup: bool = False) -> None: ...
```

Exactly one of `connection_params` and `pool`; both or neither raises `ConnectionValidationError`
(`exceptions/connection_validation_error.py`, already present, a `TransactionError`), raised in the
constructor — which, for a per-call resource, is inside the factory, while the call is running
(Clarifications). `open()` awaits `self._pool.acquire(timeout=self.acquire_timeout)` when a pool is
held, else `asyncpg.connect(**self._connection_params)`, wrapping driver failures in `HandleError`
exactly as today. `close()` sets `self._conn = None` **first** (idempotence), then returns the
connection to the pool with `await self._pool.release(conn)` or awaits `conn.close()`. The pool is
never closed. The pool annotation is the machine's own `PoolProtocol`, not `asyncpg.Pool`: the
driver must not be imported by a module that the demo and the package import at import time
(FR-037), and `asyncpg` is an optional extra.

**Rationale**: `connection_params` was required before, so defaulting it to `None` is the minimal
change that lets `pool=`-only construction be legal, and `pool` stays keyword-only so the two forms
cannot be confused positionally (FR-005). Taking the connection in `open()` and not in the
constructor follows from the constructor being synchronous (FR-004).

**A transaction left open at closing fails fast, and the connection is returned before the raise.**
The maintainer's decision, taken after this plan was first written: the resource tracks
`_in_transaction` (`begin` sets it, a successful `commit`/`rollback` clears it, a failed `COMMIT`
leaves it set), and a `close()` that finds it set issues `ROLLBACK` itself, returns the connection,
and **then** raises `TransactionLeftOpenError`, a `ResourceContractViolationError`. The rationale is the
maintainer's, stated as a principle: fail-fast — code that opened a transaction closes it, and a
framework that quietly repairs the omission lets the omission drift. "Fail-fast" is applied to the
precedence too: the violation is **the raised error even when the run already failed**, with the run's
error chained as its cause, because demoting it to a note on someone else's error would hide exactly
what the developer has to fix. Cancellation is the one case where it gives way — replacing a
`CancelledError` would break the task's own contract.
Cleaning up before raising is what keeps that strictness from turning into a leak — a raise that left
the connection unreturned would break FR-017 and FR-021, and on the failure path it would fight the
precedence rule of FR-020.

**Who can cancel a call at all — measured, because the rule has an exception for cancellation.**
The maintainer asked for the circumstances before accepting the exception, and they are four:

- **uvicorn on shutdown.** The only cancel of a *request* task in uvicorn is
  `uvicorn/server.py:289-297`: `asyncio.wait_for(..., timeout=config.timeout_graceful_shutdown)`, then
  `t.cancel(msg="Task cancelled, timeout graceful shutdown exceeded")`. A deploy or a restart while a
  request still holds a transaction is the case.
- **An MCP client.** `mcp/shared/session.py:404-406` turns a cancellation notification into
  `await self._in_flight[cancelled_id].cancel()`, so an agent or a person aborting a tool call that
  is mid-transaction is the case.
- **Application code.** `asyncio.timeout(...)` or `asyncio.wait_for(...)` around `machine.run` or a
  resource operation — the ordinary way an application bounds a slow operation. This repository has
  **zero** such call sites in `packages/*/src`, but it is the intended user-side pattern, and the
  pool's own `acquire_timeout` is exactly this on the driver's side.
- **Any parent task.** A `TaskGroup`, a supervisor or a test that cancels its child cancels ours.

Three things that do **not** cancel, recorded because each is a common assumption: an HTTP client
disconnect (uvicorn only sets `cycle.disconnected = True`, `httptools_impl.py:123`, and stops writing
— the handler runs on); this repository's own code (`cancel`, `wait_for`, `asyncio.timeout` and
`CancelledError` do not appear in `packages/*/src` at all, and every `asyncio.gather` is called with
`return_exceptions=True`); and the adapters' catch-all, which catches `Exception` while
`CancelledError` derives from `BaseException` (`CancelledError.__mro__` is
`(CancelledError, BaseException, object)`), so a cancellation already passes through as itself.

That is why the exception in FR-044 is the right shape: the cancellation comes from outside, is not
the developer's code to fix, and must stay a cancellation for the server and the MCP client to
unwind correctly. The violation is still recorded beside it, and making that record visible in a log
is [#218](https://github.com/bystrovmaxim/aoa/issues/218).

**Measured, and deliberately not relied on**: the driver would roll the transaction back by itself.
`Pool.release(conn)` reaches `PoolConnectionHolder.release`, which calls `self._con.reset(...)` unless
the connection is being closed for its query budget or its generation — and `Connection.reset()`'s
docstring states that "an open transaction (if any) is rolled back", together with cursors, `LISTEN`
registrations and advisory locks. `Connection.close()` disconnects, and the server rolls back. This is
recorded as background: the explicit `ROLLBACK` is the mechanism, and leaning on the driver's reset is
exactly the automaticity the decision rejects.

**The real pool interface**, measured against the installed driver (`asyncpg 0.31.0`), because the
issue's sketch is right in substance and wrong in one detail that matters:

- `Pool.acquire(*, timeout=None)` is **not** a coroutine function; it returns `PoolAcquireContext`,
  which supports **both** `await pool.acquire()` and `async with pool.acquire() as conn`
  (verified: `inspect.iscoroutinefunction(Pool.acquire) is False`, docstring shows both forms).
  The resource uses the two-step form — acquire in `open()`, release in `close()` — because the
  connection must outlive a single statement. `Pool.release` and `Pool.close` **are** coroutine
  functions.
- `create_pool(dsn=None, *, min_size=10, max_size=10, max_queries=50000, max_inactive_connection_lifetime=300.0, …, connect=None, **connect_kwargs)`
  — `timeout` is **not** a `create_pool` parameter, and `Pool.__init__` has no timeout either:
  `**connect_kwargs` are forwarded to `asyncpg.connect`, so `create_pool(timeout=30)` sets the
  **connect** timeout, not the wait for a free connection. `Pool._acquire(timeout)` applies exactly
  the timeout its caller passes, and `acquire()` with no argument waits forever
  (`_acquire`: `if timeout is None: return await _acquire_impl()`). So the issue's
  `create_pool(..., timeout=30)` does **not** bound pool exhaustion.
- Therefore the **size bounds are stated at creation** (`min_size`, `max_size`) and the **wait bound
  is stated where the wait happens**: the resource acquires with `timeout=self.acquire_timeout`, a
  class attribute defaulting to `30.0` that the application may state differently on its subclass.
  This keeps the constructor exactly the two forms plus `rollup` (FR-005, SC-022) and keeps every
  pool-backed resource's wait bounded (FR-010). **This is the one place the issue's sketch needed
  correcting, and the plan records it rather than following the sketch.**


**Alternatives considered**:
- *Keep the single-argument constructor and add a separate `from_pool` classmethod* — rejected: two
  construction paths with different validation is more surface than the two-form keyword rule.
- *Accept `pool` positionally* — rejected: FR-005 requires it keyword-only precisely so a positional
  argument cannot be mistaken for connection parameters.

---

## R5. Where does the application's pool live, and how does the adapter run startup and shutdown?

**Decision**: the pool lives in the application, in a small module-level holder beside the app
(`infrastructure.py` in the demo), and reaches the route through that holder — never through
`connections` (FR-012). The adapter gains **one** general lifecycle option, keyword-only, defaulting
to none, and installs it by handing it to the framework's own startup hook:

- FastAPI: `FastAPI(..., lifespan=self._lifespan)` — the application's own context manager is passed
  straight through, with no wrapper of the adapter's making. The try/finally that guarantees a close
  even when the startup body raises belongs to the application's context manager, which is the
  pattern `packages/aoa-maxitor/src/aoa/maxitor/api/app.py:65-71` already uses.
- MCP: `FastMCP(self._server_name, tools=tools, lifespan=self._lifespan)`.

**Rationale**: `mcp.server.fastmcp.FastMCP.__init__` accepts `lifespan` — measured directly on the
installed package: the parameter list includes `lifespan`, and `FastMCP` has **no** `run_async`
method. So the MCP service's lack of an ASGI hook is not a gap at all: the MCP server has its own
startup hook, and the demo's `server.run(transport=...)` already runs it
(`packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/app_mcp_service.py`). This removes the
issue's "either a new adapter option or an `app.router.lifespan_context` wrapper" choice: the option
exists and no wrapper is written.

FastAPI's own `lifespan=` is used the same way (`packages/aoa-maxitor/src/aoa/maxitor/api/app.py:65-71`
already builds one for Maxitor), so the adapter passes the application's context manager through
rather than inventing a lifecycle vocabulary.

**Alternatives considered**:
- *Let the application pass a whole `FastAPI` app* — rejected: the adapter's builder owns the app's
  middleware, handlers and health route; splitting that ownership is a larger change than one option.
- *Wrap `app.router.lifespan_context` after `build()`* — rejected: it works, but it makes every
  application repeat the wrapper and hides the hook from the adapter's own test surface. It is not
  documented as an alternative path, to avoid two ways of doing one thing.

---

## R6. Where does the hook go in the adapters, and how many places is that?

**Decision**: `connection_scope` replaces the bare `resolve_connections(...)` call at **four** sites,
all of which are the same three lines:

| Adapter | Function | Line today |
|---|---|---|
| `aoa-fastapi-adapter` | `_make_endpoint_with_body` | `adapter.py:299` |
| `aoa-fastapi-adapter` | `_make_endpoint_with_query` | `adapter.py:369` |
| `aoa-fastapi-adapter` | `_make_endpoint_no_params` | `adapter.py:468` |
| `aoa-mcp-adapter` | `_make_tool_handler` | `adapter.py:407` |

The third row is `_make_endpoint_no_params` (`adapter.py:426`), **not** `_make_endpoint`
(`adapter.py:487`), which is only the dispatcher that chooses among the three factories — a
distinction worth recording because a reader looking for the hook by name will otherwise search the
dispatcher and find nothing.

Each becomes:

```python
async with connection_scope(record.connections) as connections:
    result = await machine.run(context, action, params, connections)
```

**Rationale**: the four sites were found by searching for the call, not by guessing; each is
`connections = resolve_connections(record.connections)` immediately followed by `machine.run(...)`.
No other caller of `resolve_connections` exists in `src` (measured: the only other occurrences are
the definition, its own module, and tests). Each site becomes
`async with connection_scope(record.connections) as connections:`; the scope resolves internally (R3),
and the endpoint bodies below the `async with` are untouched — including both response-mapping paths
in the FastAPI endpoints. `resolve_connections` itself stays public and unchanged for the callers that
want only the flat mapping (R2).

**Alternatives considered**:
- *Wrap `machine.run` itself* — rejected: the machine is not the boundary that knows about
  connections; it receives `dict[str, BaseResource]` and must keep receiving only that (FR-022).
- *A decorator on each endpoint factory* — rejected: it would hide the lifecycle one level away from
  the call it governs, and the same four-line change in four places is easier to verify than a
  decorator's indirection.

---

## R7. What must the test harness fake, and why does it have to be a fake at all?

**Decision**: one **canonical** fake pool and fake connection, supplied through `pool=`, in a
test-support module under the action-machine tests. The fake enforces the driver's rule — **a
connection performs one operation at a time** — by raising an interface error on a re-entrant call,
and the fake pool enforces `min_size`/`max_size` and an acquire timeout. Two consumers need the same
thing without being able to import another package's `tests/`: the FastAPI adapter's tests and the
demo's tests get a **small stub** of their own (a pool that hands out connections and records
release), because what they prove is the wiring and the lifecycle, not contention. The
one-operation-at-a-time rule exists in exactly one place, and the contention checks live with it. The
example scripts inline a minimal stub for the same reason — they must run with no database and no
test-support import.

**Rationale**: the point of the feature is a failure that appears only under concurrency. Without a
harness that reproduces the driver's one-operation-at-a-time rule, a test against the old code
passes, and the feature's central claim — SC-001's "red on the old code, green on the new" — cannot
be made. And the repository's test suite must run with **no** database: `asyncpg` is an optional
extra (`packages/aoa-action-machine/pyproject.toml`, `[project.optional-dependencies] postgres`),
while the fake is plain Python. Supplying it through `pool=` needs no new constructor parameter,
which is what the maintainer settled in clarification.

**What the fake must reproduce, case by case**: concurrent operations on one connection fail;
acquire beyond `max_size` waits; the wait ends by timeout; release returns the connection to the
pool and a second release is refused; the pool records its high-water mark so the ceiling can be
asserted (SC-004); `close()` refuses to close a pool that resources still hold.

**Alternatives considered**:
- *`unittest.mock.AsyncMock` for the pool* — rejected: a mock returns a new child mock and never
  models contention, so the concurrency test cannot go red.
- *A real `asyncpg` pool against a real database in a container* — rejected: the constitution and
  SC-013 require no live database, and container setup would make the suite heavier than the bug.
- *Monkeypatching `asyncpg.connect`* — rejected in clarification: implicit and fragile to an import
  rename; the fake pool is explicit.

---

## R8. Which existing tests and stubs must be migrated, and which must not be touched?

**Decision**:

| Where | What changes |
|---|---|
| `test_fastapi_endpoints.py:200` | the per-call declaration gains `finalize` (positional today) |
| `test_resolve_connections.py:37` | same; `:56` (positional) gains a second argument so it still tests a bad **return**, not a missing one; `:88` (keyword) keeps testing the callable check, now on `finalize`'s sibling |
| `test_mcp_handler.py:756` | same (keyword) |
| `examples/step_17_connections/01_connections.py:96` | same (keyword) — the example is a call site too (FR-041) |
| `test_sql_resource.py`, `test_wrapper_sql_resource.py` | extended for `close()`, not rewritten; their existing double classes (`_TestConnectionManager`, `MockConnectionManager`) gain nothing, because the no-op default in `SqlResource` covers them |
| the eight demo stubs | **not touched at all** — `catalog/search_sidecar.py`, `catalog/object_store.py`, `messaging/dlq_store.py`, `messaging/outbox_primary.py`, `billing/warehouse.py`, `billing/read_replica.py`, `store/db.py`, `store/cache.py`, each a `SqlResource` subclass overriding `execute` with a no-op at line 26 |

**Rationale**: the no-op `close()` on the contract is exactly what buys the last row; without it,
eight files across four demo domains would each need an edit to stay abstract-instantiable, and the
test doubles would need the same. The migrated sites are named by file and line so that the change is
checkable rather than remembered (SC-018).

**How the concurrency test is made red, since the old code cannot run it.** The old resource had no
`pool=` parameter, so a pool-injected test cannot be executed against the old code at all, and
monkeypatching the driver is rejected (R7). SC-019 is therefore realized the way the constitution
describes verification: by the **adversarial break** (FR-043). With the new test in place, the
implementation is temporarily broken the way the test must catch — the sharpest break is to make every
resource share one connection (a module-level connection handed out by `open()`, or a pool whose
`acquire` always returns the same connection) — the concurrency test is run and must fail with the
one-operation-at-a-time error and nothing else newly failing, and then the break is removed and the
test is run green. Both directions are recorded.


---

## R9. How is the demo extended without a database, and what makes it importable without the driver?

**Decision**: the existing `identity` domain gains a resource subclass with one read method and one
transactional method, an action that declares it with `@connection`, a route that declares it per
call with both lambdas, and a pool in the demo's `infrastructure.py` created only when a DSN is
present. The demo's `pyproject.toml` gains a `postgres` extra carrying the driver, and the demo's
tests use a fake pool, so the suite is green with no PostgreSQL and with the extra absent.

**Rationale**: measured — `packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/infrastructure.py`
already holds the shared machine and auth for both transports, which is where a holder belongs; the
FastAPI service builds its app through `FastApiAdapter(...).build()`, which is where the new
lifecycle option is passed; and the MCP service calls `server.run(...)` on the object `build()`
returns, which now carries the same lifespan through `FastMCP`. Importing the demo without the
driver must be safe: the resource module must not import the driver at module import time — it takes
its connection through `pool=` and gets its connection parameters as data, so only the pool's
creation needs the driver, and that creation is behind the DSN check.

**Alternatives considered**:
- *A new demo domain* — rejected by the maintainer in clarification: extend `identity`.
- *Make `asyncpg` a hard dependency of the demo* — rejected: it would break `pip install aoa-demo`
  for anyone without a database, which the acceptance forbids.

---

## R10. What settles the version question, and what does the stale-fragment sweep look for?

**Decision**: the feature writes its article under `## [Unreleased]` in
`packages/aoa-action-machine/CHANGELOG.md` (with `### Breaking changes`) and in
`packages/aoa-demo/CHANGELOG.md`, and introduces **no** dated version heading and **no** version
bump. The sweep searches for `PostgresResource`, `_conn`, `asyncpg.connect`, `create_pool`,
`acquire`, `PerCallConnection`, `finalize` and `connection_scope` across `packages/*/src`, `docs/`,
`examples/` and the tests.

**Rationale**: the maintainer corrected the earlier reading of this question. A version in
`pyproject.toml` names the version **under development**, not a release; `948a2e66` (#207) raised
three `pyproject.toml` versions without touching any changelog, and no release followed it. Writing
a dated heading would therefore date a release that never happened, and would move other people's
pending bullets under it. The release — renaming `## [Unreleased]` to a version, with the date — is
the maintainer's act. The sweep's term list is the issue's own, plus the two new names introduced
here, because a new name is exactly what a stale page will lack.

**Alternatives considered**:
- *Bump to `1.0.1a4`* — rejected: the version already published in metadata would then never have
  existed as a release, and the changelog would carry a phantom.

---

## R11. What does this plan deliberately not resolve?

- **The exact dialect of the acquire timeout call.** Whether the demo passes the wait bound to
  `create_pool` where the driver supports it or to `acquire(timeout=...)` is a demo-level detail;
  the requirement is that the wait is bounded and that the bound is stated (FR-010). Research
  recorded the driver's real signature so the implementation does not copy the issue's sketch
  blindly.
- **The wording of the new documentation section.** The spec fixes its content, title, placement and
  exercise (FR-030); how the prose reads is the writing task's business, not the plan's.
- **The demo's exact read and transactional method names.** The spec requires one of each and the
  issue requires them to be true to the identity domain; names are chosen when the code is written.
