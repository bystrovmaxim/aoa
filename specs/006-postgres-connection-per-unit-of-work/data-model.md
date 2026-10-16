# Phase 1 — Data Model: One connection per unit of work, and one pool for the process

**Feature**: `specs/006-postgres-connection-per-unit-of-work` · **Date**: 2026-10-16

This feature persists nothing: there is no schema, no migration and no stored row. Its "data" is the
objects that own a connection and the states one of them passes through while it owns one, so what
follows is a model of **ownership and state**, derived from [spec.md](./spec.md). Paths and line
numbers name the code as it stands before the change.

## E1. Pool

The process-wide store of reusable connections (FR-008, FR-009, Key Entities).

| | |
| --- | --- |
| **Owner** | the application, created in its lifespan and closed there (FR-008); never the framework |
| **Type** | relied on structurally through the machine's `PoolProtocol`; the driver's own `create_pool` result satisfies it — see [contracts/sql-resource.md](./contracts/sql-resource.md) §6 |
| **Members** | an `acquire(*, timeout=None)` returning an awaitable proxy, an awaitable `release(conn)`, an awaitable `close()` |
| **Stated bounds** | `min_size=1, max_size=10` at creation, and `30` as the wait bound where the wait happens — the resource's `acquire_timeout`, since the driver's pool creation accepts no wait bound (FR-009, research R4) |
| **Cardinality** | one per application; several per process is out of scope |

- **DM-001**: Not a connection and never in `connections` (FR-012); it reaches routes through the
  application's holder (E7).
- **DM-002**: Reaching the ceiling does not fail immediately: `acquire()` waits, then ends in a named
  failure once `timeout` passes (FR-010, FR-011).
- **DM-003**: The pool outlives every resource borrowed from it; a release never closes it (FR-006).
  A resource constructed without `pool=` must not reach any pool (FR-007).

## E2. Resource

The unit of work's handle on a database — `PostgresResource` and its `SqlResource` contract.

| Attribute | Meaning |
| --- | --- |
| `_connection_params: dict[str, Any] \| None` | parameters for the resource's own connection; `None` when pooled |
| `_pool` | the pool borrowed from, or `None` when the resource owns its connection (new field) |
| `_conn` | the held connection, or `None`; written only by `open()`, cleared only by `close()` |
| `_in_transaction: bool` | whether the caller has a transaction open; set by `begin()`, cleared by `commit()`/`rollback()` on success (new field) |
| `_rollup: bool` | `SqlResource.__init__` (`sql_resource.py:102`); unchanged |

- **DM-004**: Exactly one of `_connection_params` and `_pool` is non-`None`, fixed at construction
  (FR-005).
- **DM-005**: At most one connection is held, only for one unit of work (FR-001); every operation —
  `begin`, `execute`, `commit`, `rollback` — runs on it (FR-002, FR-027).
- **DM-006**: `_conn` is written only inside `open()` and cleared only inside `close()` (FR-004); the
  resource never closes `_pool`, and never touches a pool it was not given (FR-007).
- **DM-006a**: `_in_transaction` is the caller's obligation made visible. `begin()` sets it; `commit()`
  and `rollback()` clear it **on success** (a rollup commit clears it through `rollback`). A failed
  `COMMIT` leaves it set, because the resource cannot claim the transaction ended (FR-044).

## E3. Unit of work

Not a class: the interval between one resource's `open()` and its `close()` within one call.

- **DM-007**: Two units of work never share a connection, and no statement of one runs inside the
  other's transaction (FR-001 to FR-003).
- **DM-008**: A unit of work that raises, is cancelled or is finalized releases its connection just
  the same; none ends with a connection held (FR-006, FR-017, SC-004).

## E4. Per-call declaration — `PerCallConnection`

`resources/per_call_connection.py:19`.

| Field | Type | Position |
| --- | --- | --- |
| `factory` | `Callable[[], BaseResource]` | first |
| `finalize` | `Callable[[BaseResource], Awaitable[None] \| None]` | second, mandatory |

- **DM-009**: Order is `factory, finalize`, so keyword call sites that pass only `factory=` keep
  resolving — they fail validation for the missing finalizer, not for their keyword.
- **DM-010**: The pair is mandatory at declaration time; no finalizer, or a non-callable one, is
  rejected when the record is built (FR-014, SC-007).
- **DM-011**: A factory returning the same shared object on every call is neither rejected nor
  detected; no marker and no comparison is added (FR-014, Clarification).

## E5. Finalizer

- **DM-012**: Called by the boundary exactly once per resolved resource, in a finalization step that
  runs on success, on exception and on cancellation (FR-017); synchronous or asynchronous (FR-015).
- **DM-013**: It runs for a per-call resource without a lifecycle too (FR-018), and even when a later
  resource of the same call failed to open (FR-021).
- **DM-014**: It never closes the pool (FR-007).

## E6. Nested-action proxy — `WrapperSqlResource`

`resources/sql/wrapper_sql_resource.py:48`.

| Member | After the change |
| --- | --- |
| `open`, `begin`, `commit`, `rollback` | raise `TransactionProhibitedError` (already) |
| `close`, `__aenter__`, `__aexit__` | raise `TransactionProhibitedError` (new) |
| `execute`, `rollup`, `check_rollup_support` | delegate to `_connection_manager` (unchanged) |
| `acquire` | absent; no way to take a connection is exposed (FR-024) |

- **DM-015**: The proxy runs on its caller's connection, so a nested call stays inside that
  transaction and `rollup` keeps working (FR-025).
- **DM-016**: `isinstance(wrapper, ProtocolSqlResource)` stays true (FR-024).

## E7. Holder

The application-scoped place carrying the pool to the routes, since the action never receives it
(FR-012).

- **DM-017**: Application state, not domain state; it holds the pool, never a connection.
- **DM-018**: Reading it before it is filled is a named failure, not an `AttributeError` (FR-013).
- **DM-019**: Not a framework type: this feature fixes the obligation, not the class.

## E8. Boundary

The adapters that serve calls — `FastApiAdapter`, `McpAdapter`
([contracts/boundary.md](./contracts/boundary.md)).

- **DM-020**: It creates per-call resources, opens those with a lifecycle before the run, and
  finalizes them after it on every path (FR-016, FR-017).
- **DM-021**: It opens and closes nothing supplied ready (FR-019), and `machine.run` still receives
  only `dict[str, BaseResource]` (FR-022).

## Resource state transitions

States: **Constructed** (no connection), **Open-owned** (`_conn` from `_connection_params`),
**Open-borrowed** (`_conn` from `_pool`), **Closed** (`_conn is None`). Orthogonal to those, the
transaction flag `_in_transaction` is either **idle** or **in transaction** — a resource can be
Open-owned and in transaction at the same time.

| Event | From | Result | Basis |
| --- | --- | --- | --- |
| `open()` | Constructed | Open-owned or Open-borrowed | FR-004 |
| `open()` on an already Open resource | Open | no-op; the held connection is kept, not replaced | Edge case; settled below |
| `open()` | Closed | Open again, safe | FR-006 edge, US4 scenario 3 |
| `close()` | Open-owned | Closed; connection closed | FR-006 |
| `close()` | Open-borrowed | Closed; connection released, pool stays open | FR-006 |
| `close()` | Constructed | no-op, no error | FR-006, US4 scenario 2 |
| `begin()` | Open, idle | Open, in transaction | FR-044 |
| `commit()` / `rollback()` succeeds | Open, in transaction | Open, idle | FR-044 |
| `commit()` fails | Open, in transaction | unchanged — stays in transaction | FR-044 |
| `close()` | Open, in transaction | Closed; the resource issues `ROLLBACK`, returns the connection, **then raises** `TransactionLeftOpenError` | FR-044 |
| `close()` twice | Closed | no-op; not returned twice, and nothing raised | FR-006, FR-044 |
| `close()` after cancellation | Open | still closes (finalizer path) | FR-017, US1 scenario 4 |
| `open()` raises | Constructed | stays Constructed; `HandleError` surfaces; already-opened siblings are still finalized | FR-021 |
| `close()` raises an operational error | Open | surfaces on a clean run; on a failed run the run's own error is what the caller sees, the closing failure recorded beside it | FR-020 |
| `close()` raises a contract violation | Open, in transaction | the violation is the raised error on both runs; a failed run's error becomes its cause | FR-044 |

**Double `open()`** — settled in the design: opening an already-open resource returns immediately and
**keeps the connection it already holds**; it does not take a second one. Replacing it would drop a
connection with nothing left to release it, which is the leak this feature exists to remove. The
state model therefore has exactly two states a resource can be in — no connection, and one connection
— and `open()` is the transition into the second. Together with the idempotent `close()`, this is what
makes open → close → open safe (FR-006, Edge Cases).

**Why this does not raise the repository's existing `ConnectionAlreadyOpenError`.** That error exists
for a store whose `open()` owns a live session it must not silently replace
(`packages/aoa-ocel/src/aoa/ocel/resource/in_memory_ocel_store_resource.py:60`). Here the resource is
opened by the boundary and closed by the finalizer on every path, so a second `open()` is an ordinary
consequence of the lifecycle rather than a misuse, and raising would make a legal path fail. The
different answer is deliberate, and the docstring says so.

## Validation rules

| Rule | Error | Raised where |
| --- | --- | --- |
| a transaction is open when the resource is closed | `TransactionLeftOpenError(ResourceContractViolationError)` — raised after the rollback and the return, and it outranks the run's own error | `PostgresResource.close()` (FR-044) |
| both `connection_params` and `pool` given | `ConnectionValidationError` | `PostgresResource.__init__` (FR-005) |
| neither given | `ConnectionValidationError` | `PostgresResource.__init__` (FR-005) |
| declaration with no `finalize` | `TypeError` (missing required field) | the declaration's construction (FR-014) |
| `finalize` not callable | `TypeError("PerCallConnection.finalize must be callable.")` | `validate_connection_entries` (FR-014) |
| duplicate connection key | `ValueError("Duplicate connection key: …")` | `validate_connection_entries:45`, defensively `resolve_connections:77` |
| key not a non-empty string | `TypeError("Connection key must be a non-empty string.")` | `validate_connection_entries:43`, `resolve_connections:75` |

The construction error is raised at the resource's construction and only there; validating a
declaration's callables never calls the factory (FR-014, Clarification).

## Ownership: the three cases (FR-030)

| What is in `connections` | Who opens | Who closes |
| --- | --- | --- |
| a ready `BaseResource` supplied directly | whoever supplied it (the application); the framework does not | the same owner; the boundary does not |
| `PerCallConnection` whose factory returns a resource with `open` | the boundary, before the run (FR-016) | the declaration's `finalize`, in `finally` (FR-017) |
| `PerCallConnection` whose resource has no lifecycle | nobody (FR-018) | the declaration's `finalize`, in `finally` (FR-018) |

In all three cases the connection is taken at open, not at construction (FR-004), and the pool is
never in `connections` (FR-012).

## What is deliberately not modelled

- **A shared resource returned by a per-call factory.** Not detected, no marker (FR-014, Clarification).
- **Sessions, per-user state, several pools per process.** One pool per application (Out of scope).
- **Statement-cache modes.** The driver's prepared-statement caching is untouched (Out of scope).
- **Retries and circuit breakers.** A failing acquire or statement is not retried (Out of scope).
- **The generic query surface.** No new public query method; [#216](https://github.com/bystrovmaxim/aoa/issues/216) owns it (FR-026).
