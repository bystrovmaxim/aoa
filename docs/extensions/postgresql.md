<!-- translated-from: postgresql_draft.md @ 2026-06-17T10:44:44Z · sha256:6b05aba3f45e -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# PostgreSQL — a transactional resource on asyncpg

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [What it is](#what-it-is)
- [Installation](#installation)
- [The SQL stack: protocol → manager → wrapper](#the-sql-stack-protocol--manager--wrapper)
- [Setup](#setup)
- [Rollup: a run against the production schema without writing](#rollup-a-run-against-the-production-schema-without-writing)
- [API surface](#api-surface)

---

`PostgresResource` is a built-in [`Resource`](../tutorials/step-19-resource.md): a transactional connection to PostgreSQL on top of `asyncpg`. As befits a resource, it is **pure transport** — open a connection, run a query, commit; no business decisions. The business logic lives in the operation, the resource answers only the question "how to fetch".

> There is no runnable example here: it would need a live PostgreSQL database. The API is verified against the source; the rollback (rollup) mechanics are shown on an in-memory resource in the chapter [Substituting the environment](../tutorials/step-24-substitution.md#rollup-a-live-database-without-persisting).

## What it is

`PostgresResource(connection_params, *, rollup=False)` — a subclass of `SqlResource`. `connection_params` are passed to `asyncpg.connect(...)`. It supports the full transactional cycle and rollup mode.

## Installation

```bash
pip install "aoa-action-machine[postgres]"
```

## The SQL stack: protocol → manager → wrapper

The resource follows the canonical three-part pattern for transactional resources (which is also the template for [«your own resource»](../index.md#how-to-write-your-own-extension)):

- **`ProtocolSqlResource`** — a typed protocol: `rollup`, `check_rollup_support`, `open`, `begin`, `commit`, `rollback`, `execute`.
- **`PostgresResource`** (on top of `SqlResource`) — the real manager: connection, transactions, queries.
- **`WrapperSqlResource`** — the wrapper for **nested** operations: it delegates `execute` but raises `TransactionProhibitedError` on `open/begin/commit/rollback`. The transaction belongs to the root operation; a nested one only runs commands. The wrapper is returned by `get_wrapper_class()`, and the runtime substitutes it automatically.

This is exactly the boundary covered in the chapters on [Resource](../tutorials/step-19-resource.md#a-wrapper-for-nested-operations) and [dependencies](../tutorials/step-06-dependencies.md): a nested step cannot commit or roll back someone else's transaction.

## Setup

The connection is built by the owner and supplied to the operation as a [`@connection`](../tutorials/step-06-dependencies.md); the aspect reads it by key and works with the transport:

```python
from aoa.action_machine.resources.postgres import PostgresResource

db = PostgresResource({"dsn": "postgresql://user:pass@localhost/shop"})
await db.open()
# machine.run(ctx, SomeAction(), params, connections={"db": db})  — aspect: connections["db"].execute(...)
```

Inside the operation an aspect calls `connections["db"].execute(query, params)`; opening/committing the transaction is controlled by the owner, and nested operations receive a wrapper with no right to do so.

## Rollup: a run against the production schema without writing

`SqlResource` (and therefore `PostgresResource`) supports rollup natively: `check_rollup_support()` → `True`, and with `rollup=True` the `commit()` method performs a **rollback instead of a real commit** — the `COMMIT` command never reaches the database. This lets you [test](../tutorials/step-24-substitution.md#rollup-a-live-database-without-persisting) an operation against the production schema and real DB constraints without persisting a single change:

```python
db = PostgresResource({"dsn": "..."}, rollup=True)   # commit -> rollback
```

## API surface

`PostgresResource` (through `ProtocolSqlResource`): `open()` · `begin()` · `execute(query, params=None)` · `commit()` (or rollback under rollup) · `rollback()` · the `rollup` property · `check_rollup_support()` · `get_wrapper_class()` → `WrapperSqlResource`.

What a resource is and why it is separated from the operation — the chapter [Resource](../tutorials/step-19-resource.md); your own data source behind the same contract — [«Your own resource»](../index.md#how-to-write-your-own-extension).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
