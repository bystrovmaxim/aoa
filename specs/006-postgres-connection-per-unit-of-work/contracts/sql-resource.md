# Contract: the SQL resource after this change

**Feature**: `specs/006-postgres-connection-per-unit-of-work` · **Date**: 2026-10-16

The surface every SQL resource is obliged to offer once closing joins it, and the surface the driver
keeps. A reader of this contract should be able to tell, without reading the driver, whether a
proposed change breaks it.

Modules:
`resources/sql/protocol_sql_resource.py`, `resources/sql/sql_resource.py`,
`resources/sql/wrapper_sql_resource.py`, `resources/postgres/postgres_resource.py`.

---

## 1. Construction — the two forms (FR-005)

```python
class PostgresResource(SqlResource):
    def __init__(
        self,
        connection_params: dict[str, Any] | None = None,
        *,
        pool: PoolProtocol | None = None,
        rollup: bool = False,
    ) -> None: ...
```

- **SR-1.1** Exactly one of `connection_params` and `pool` must be non-`None`. Both, or neither,
  raises `ConnectionValidationError` from the constructor — at construction, not at the first call
  (FR-005; `exceptions/connection_validation_error.py`).
- **SR-1.2** `pool` is keyword-only, so the two forms cannot be confused positionally (FR-005).
- **SR-1.3** `rollup` keeps its place and its meaning; `SqlResource.__init__` still stores `_rollup`
  (`sql_resource.py:100-102`, FR-027).
- **SR-1.4** The constructor is synchronous and takes no connection; no connection is acquired here
  (FR-004).

## 2. `open()` and `close()`

| Method | Guarantee |
| --- | --- |
| `open()` | every later operation of this resource has a connection: `_conn` is taken from `_pool` or created from `_connection_params` (FR-004). A failure raises `HandleError` and leaves `_conn is None`. |
| `close()` | no connection is held afterwards: an owned connection is closed, a borrowed one is released to the pool (FR-006). If a transaction is still open, the resource rolls it back itself, returns the connection, and then raises `TransactionLeftOpenError` (FR-044). |

- **SR-2.1** `close()` is idempotent: on a resource that holds nothing — never opened, or already
  closed — it is a no-op, and it never hands the same connection back twice (FR-006).
- **SR-2.2** `close()` never closes the pool, and a resource built with `connection_params` never
  reaches a pool (FR-007).
- **SR-2.3** Pool exhaustion is bounded: `acquire()` waits, and the wait ends in a named failure
  once the pool's `timeout` passes (FR-010).
- **SR-2.4** A closed resource may be opened again; closing it again is safe (FR-006 edge, US4
  scenario 3).
- **SR-2.5** A transaction left open at closing is a **failure the caller hears about**, not one the
  driver quietly repairs. The resource tracks it (`_in_transaction`, set by `begin`, cleared on a
  successful `commit`/`rollback`), issues `ROLLBACK` itself, returns the connection, and only then
  raises `TransactionLeftOpenError` — a `ResourceContractViolationError`, the family that says the
  caller's own code broke the contract (FR-044). That error is the raised one even when the run had
  already failed, with the run's error as its cause; cancellation is the only case where it gives way,
  and then it is recorded beside the `CancelledError`. Two consequences are part of the contract: because the
  connection is returned **before** the raise, finalization is complete even when `close()` raises;
  and because the resource is now empty, a second `close()` is a silent no-op (SR-2.1).
- **SR-2.6** The driver would roll the transaction back anyway — `Pool.release` resets the connection
  (`asyncpg.pool.PoolConnectionHolder.release` calls `Connection.reset`, whose docstring states that an
  open transaction is rolled back) and a closed connection is rolled back by the server. The
  implementation **does not rely on that**: the explicit `ROLLBACK` in SR-2.5 is what makes the
  resource's own state honest, and relying on the driver's reset is exactly the drift this rule
  refuses. The driver's behaviour is recorded as background, not as the mechanism.
- **SR-2.7** A `close()` that finds no open transaction raises nothing (FR-006), and a resource whose
  `open()` was never reached is finalized without an error (FR-017, FR-021).

## 3. `close()` in the contract, and the eight stubs (FR-023)

- **SR-3.1** `ProtocolSqlResource` gains `async def close(self) -> None: ...` with a **concrete
  no-op body**, beside `open`/`begin`/`commit`/`rollback`/`execute`
  (`protocol_sql_resource.py:51-69`).
- **SR-3.2** `SqlResource` gains the same concrete no-op `close()`, so every descendant inherits a
  real body and no subclass is obliged to implement one.
- **SR-3.3** The eight demo stubs subclass `SqlResource` and therefore need **no edit**: 
  `model/catalog/resources/search_sidecar.py` (`CatalogSearchSidecar`),
  `model/catalog/resources/object_store.py` (`CatalogObjectStore`),
  `model/messaging/resources/dlq_store.py` (`MessagingDeadLetterStore`),
  `model/messaging/resources/outbox_primary.py` (`OutboxPrimaryDatabase`),
  `model/billing/resources/warehouse.py` (`BillingWarehouse`),
  `model/billing/resources/read_replica.py` (`BillingReadReplica`),
  `model/store/resources/db.py` (`StorefrontDatabase`),
  `model/store/resources/cache.py` (`StorefrontSessionCache`).
- **SR-3.4** Only the driver implements `close()` for real (SR-2.1 to SR-2.3, SC-010, SC-012).

## 4. The transaction surface is unchanged (FR-027)

- **SR-4.1** `begin()`, `commit()`, `rollback()` keep their contract and now act on `_conn`, the
  connection this resource holds (FR-002).
- **SR-4.2** `commit()` still performs `rollback()` when `rollup` is true
  (`sql_resource.py:127-133`, `postgres_resource.py:102-120`).
- **SR-4.3** `rollup` and `check_rollup_support()` are unchanged; `WrapperSqlResource` still
  delegates `rollup` to the wrapped manager.

## 5. What the wrapper forbids (FR-024)

`WrapperSqlResource` (`wrapper_sql_resource.py:48`):

- **SR-5.1** `close`, `__aenter__` and `__aexit__` join `open`, `begin`, `commit`, `rollback` in
  raising `TransactionProhibitedError`. A nested action cannot end or alter its owner's connection.
- **SR-5.2** It exposes no `acquire`. There is no way to take a connection through it (US4 scenario 5).
- **SR-5.3** `isinstance(wrapper, ProtocolSqlResource)` stays true; adding the members above keeps
  the structural match intact (FR-024, SC-011).
- **SR-5.4** `execute` keeps delegating to `_connection_manager`, so a nested call runs on its
  caller's connection and inside its caller's transaction (FR-025).

## 6. The pool contract the resource relies on

The framework defines no pool type. The resource relies on this structure, which the driver's pool
and the tests' fake pool both satisfy (FR-042):

```python
class PoolProtocol(Protocol):
    def acquire(self, *, timeout: float | None = None) -> Any: ...  # awaitable / async-CM proxy
    async def release(self, conn: Any) -> None: ...
    async def close(self) -> None: ...
```

- **SR-6.1** `acquire` is deliberately **not** declared `async def`: the driver's `Pool.acquire` is an
  ordinary method returning a proxy that supports both `await` and `async with` (`asyncpg 0.31.0`,
  research R4). The resource uses the two-step form — `await pool.acquire(timeout=…)` in `open()`,
  `await pool.release(conn)` in `close()` — because the connection outlives a single statement.
  `release` and `close` are coroutine functions.
- **SR-6.2** The pool's **size** is stated where the pool is created: the examples and the demo carry
  `min_size=1, max_size=10` (FR-009). The **wait bound** cannot be stated there — the driver's
  `create_pool` accepts no such parameter, and `Pool.acquire()` defaults to waiting forever — so it is
  stated where the wait happens: the resource acquires with `timeout=self.acquire_timeout`, a
  class-level attribute defaulting to `30.0` that the application may state differently on its
  subclass. That is how the constructor stays exactly the two forms plus `rollup` (FR-005, SC-022)
  while the wait stays bounded (FR-010); the examples and the demo carry the value `30` there. The
  framework never supplies, configures or closes the pool (FR-008, Assumptions).
- **SR-6.3** The resource calls `acquire`/`release` only; it never calls `close` on the pool (FR-007).
- **SR-6.4** Tests supply a fake pool and a fake connection through `pool=`; the constructor gains no
  substitution parameter (FR-042, SC-022).
- **SR-6.5** A `release` that raises is a closing failure like any other: it surfaces on a clean run
  and is recorded beside the run's error on a failed run (FR-006, FR-020).

## 7. Explicit non-changes

- **SR-7.1** No new public query method. The public generic query surface is neither added to nor
  removed; moving it to protected driver helpers is [#216](https://github.com/bystrovmaxim/aoa/issues/216)
  (FR-026).
- **SR-7.2** The home page's read examples that run through `execute()` stay as they are (FR-026).
- **SR-7.3** `SqlResource.get_wrapper_class()` still returns `WrapperSqlResource`
  (`sql_resource.py:113-115`); Maxitor is not touched (FR-028).
