# Phase 1 — Data Model: The query surface leaves the SQL contract, and the driver keeps protected helpers

**Feature**: `specs/007-sql-contract-driver-helpers/spec.md` · **Date**: 2026-10-17

This feature moves a member rather than creating a subsystem, so the model below is the set of shapes whose
membership changes and the states they can be in. Nothing here is persisted; every shape is a Python object, and
the only external system is the database driver, which the tests replace.

## E1. SQL resource contract — `ProtocolSqlResource`

A `@runtime_checkable` structural type (`protocol_sql_resource.py:38`) that says what every SQL resource is obliged
to answer. Its members after this change: `rollup` (property), `open`, `begin`, `commit`, `rollback`, `close`.
`execute` is not among them.

- **Why it is an entity**: it is the type the framework and the fixtures are written against, so a member leaving it
  is what makes the obligation disappear from every subclass at once.
- **Validation**: the contract is checkable at runtime (`isinstance`), which is what makes the proxy's continued
  satisfaction a test rather than an assertion in prose.
- **Prose bound to it**: the `PURPOSE` sentence (`:12`), the module title (`ProtocolSqlResource — structural contract
  for transactional SQL access`), and the AI-CORE `CONTRACT` key (`:43`).

## E2. Base resource — `SqlResource`

The abstract base every hand-written SQL resource inherits. Members after the change: `open`, `begin`, `rollback`
abstract; `commit` concrete and rollup-aware; `close` concrete and harmless (`#215`); `rollup` property;
`check_rollup_support`; `get_wrapper_class`.

- **Validation (FR-004)**: a subclass implementing only `open`, `begin` and `rollback` instantiates; the three
  abstract members are what `TypeError` is raised for, and there is no fourth.
- **Prose bound to it**: the contract line (`:11`), the rollup walk-through (`:52-53`), and the diagram.

## E3. Driver — `PostgresResource`

The one class that holds a connection and knows the driver's error types. Members after the change: `open`,
`begin`, `commit`, `rollback`, `close`, `_require_connection`, `_execute`, `_fetchrow`. Construction and closing are
unchanged from `#215` (`PostgresResource(connection_params)` or `PostgresResource(pool=pool)`, exactly one).

- **State**: `_conn: Connection | None` and `_in_transaction: bool` (both from `#215`), plus the derived state "open
  or not", which is what the single check reads.
- **Validation (FR-006, FR-007)**: a helper called while `_conn is None` raises `HandleError("Connection is not
  open")`; a failure raised by the connection is turned into `HandleError` with the driver's error as `__cause__`.

## E4. Protected helper

A member of the driver that a subclass calls and nothing else can reach, in two shapes:

| Helper | Answers | Failure |
| --- | --- | --- |
| `_execute(query, params=None)` | the driver's command status, `str` | `HandleError("SQL execution failed: …")`, cause chained |
| `_fetchrow(query, params=None)` | the first row as `asyncpg.Record`, or `None` | the same |

- **Parameters**: `params: tuple[Any, ...] | None`; `None` and `()` both mean "no parameters".
- **Must not**: open or end a transaction, convert a row into a mapping, or compose a message of its own beyond the
  one above.
- **Callers after this change**: `IdentityStore` (the demo), through its two primitives — the statement helper for
  the write and the row helper for the read. That is what keeps the set at two (FR-008).
- **Not in this entity**: `_fetch` (several rows), `_fetchval` (one value), `executemany` (many parameter sets) — no
  caller needs them after the demo's read becomes single-row (Clarifications, R3).

## E5. Nested-action proxy — `WrapperSqlResource`

What a nested action receives in place of the resource its caller holds. Members after the change: refusals for
`open`, `begin`, `commit`, `rollback`, `close`, `__aenter__`, `__aexit__`; `rollup` and `check_rollup_support`
delegated to the owner; `get_wrapper_class()` returning itself.

- **Invariant (FR-011)**: no query member of any kind — public or protected — and no way to acquire a connection.
- **Invariant (FR-012)**: every lifecycle operation is refused with `TransactionProhibitedError`.
- **Invariant (FR-006, R4)**: it still satisfies `ProtocolSqlResource`, so `isinstance(proxy, ProtocolSqlResource)`
  is true and a second and a third wrap behave as the first.

## E6. Domain wrapper

A resource's own proxy, substituted through `get_wrapper_class()`. It delegates the resource's semantic methods to a
nested action and refuses the lifecycle exactly as the default proxy does. The repository's existing example is
`OcelStoreWrapper` (`packages/aoa-ocel/src/aoa/ocel/resource/ocel_store_wrapper.py`), which delegates `add_event` and
refuses `open`/`close`.

- **Where it is chosen**: `ToolsBox._wrap_connections` (`tools_box.py:191`) asks the resource for its wrapper class
  and constructs it; that is the only construction site in the framework.
- **Why it matters here**: with the proxy delegating nothing, this is the only way nested access is given, and it is
  the shape the guidance teaches (FR-013, FR-018, FR-022).

## E7. Driver-free storage primitive

The pair of protected operations a driver-free base declares so that one domain runs over PostgreSQL and in memory.
After this change: `_read_person(person_id) -> dict[str, Any] | None` and `_write_login(person_id, at) -> None`.

- **Implementations**: `IdentityStore` routes the read through `_fetchrow` and the write through `_execute`, and
  converts the driver's `Record` into a plain mapping; `IdentityStoreStub` answers both from its dictionaries.
- **Invariant (FR-016, SC-017)**: no implementation decides what to do by inspecting the text of a statement — the
  sniffing at `identity_store_stub.py:69` disappears with the member that required it.

## E8. Unit of work

One call's use of a resource: open, transact, close, on the resource's own connection (`#215`). Unchanged by this
feature, but it is the boundary that says what a helper call belongs to: a statement run through `_execute` runs on
this unit of work's connection and inside its transaction, and rollup mode still rolls the transaction back.

## Access paths — who may run a statement, and with what

| Holder | May run a statement? | With what |
| --- | --- | --- |
| The resource that owns the connection | yes | `_execute` / `_fetchrow`, the protected helpers |
| A domain method on that resource | yes | the same, or its own protected primitive over them |
| A nested action, handed the default proxy | no | nothing — the proxy has no query member at all |
| A nested action, handed a domain wrapper | only what the domain delegates | the wrapper's own semantic method |
| Any caller of the public contract | no | the contract has no query member |

## State transitions

**The resource** (unchanged from `#215`, restated because the check reads the first state):

| From | Event | To | Notes |
| --- | --- | --- | --- |
| not open (`_conn is None`) | `open()` | open | takes the connection; idempotent |
| open | `close()` | not open | returns the connection; a second close is silent; a transaction still open is ended and then reported (FR-044 of `#215`) |
| open, not in a transaction | `begin()` | open, in a transaction | |
| open, in a transaction | `commit()` / `rollback()` | open, not in a transaction | `commit()` in rollup mode goes through `rollback()` |
| not open | any helper | not open | `HandleError("Connection is not open")`, no state change |

**The helper call**: (not open → refused) · (open, connection succeeds → the status or the row, state unchanged) ·
(open, connection fails → `HandleError` with the driver's error as its cause, state unchanged). The helper never
changes the resource's state, which is why it cannot hide a transaction from the domain that owns it.

**The proxy**: one state only. It holds a reference to the owner and answers refusals, `rollup` and its own class;
nothing it does changes the owner's state.

## Validation rules, traced to the requirements

| Rule | Where it comes from |
| --- | --- |
| A subclass needs `open`, `begin` and `rollback`, and nothing else | FR-004 |
| A helper on a resource that is not open, or is closed, raises `HandleError("Connection is not open")` | FR-006 |
| A driver failure arrives as `HandleError` with the driver's error chained | FR-007 |
| Every helper has a caller inside `packages/`; no helper beyond the two exists | FR-008 |
| `params=None` and `params=()` are the same call | FR-005, R3 |
| The proxy exposes no query member and still satisfies the contract | FR-011, FR-012 |
| A domain wrapper delegates its own methods and refuses the lifecycle | FR-013 |
| The in-memory store inspects no statement text | FR-016, SC-017 |
| No public query member exists anywhere under `packages/` | FR-001 … FR-004, SC-001 |

## What is deliberately not modelled

- **A query API**: the feature removes one rather than introducing one; there is no statement object, no result
  wrapper, no row mapper beyond the demo's own `dict(...)`.
- **Transaction management in a helper**: the unit of work owns the transaction, and the helpers deliberately know
  nothing about it.
- **Timeouts, retries and cancellation**: `#215` gave the resource its wait bound and the scope its lifecycle;
  neither is revisited.
- **The driver's record type beyond the boundary**: `asyncpg.Record` appears in the helper's signature and stops at
  the PostgreSQL store, which converts it; no domain type below that boundary mentions the driver.
