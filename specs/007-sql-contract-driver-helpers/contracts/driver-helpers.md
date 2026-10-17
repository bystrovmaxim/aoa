# Contract: the driver's protected helpers

**Feature**: `specs/007-sql-contract-driver-helpers/spec.md` · **Date**: 2026-10-17

This contract fixes the extension point that replaces the removed member. It is normative: the two helpers and the
one check are what a domain resource over PostgreSQL is written against, and everything they deliberately do not do
is as binding as what they do.

## 1. The two helpers

```python
def _require_connection(self) -> asyncpg.Connection[asyncpg.Record]: ...
async def _execute(self, query: str, params: tuple[Any, ...] | None = None) -> str: ...
async def _fetchrow(self, query: str, params: tuple[Any, ...] | None = None) -> asyncpg.Record | None: ...
```

**DH-1.1** `_execute` MUST run the statement on the connection the resource holds and MUST return the driver's
command status as a string — the shape `asyncpg.Connection.execute` has, which discards rows. A statement with
`RETURNING` therefore answers with a status and not with rows, and the guidance says so.

**DH-1.2** `_fetchrow` MUST return the connection's first row as the driver's record type, or `None` when the query
returned nothing. It MUST be documented as answering the **first** row, not the only row: a query that can match
several rows without an ordering yields an arbitrary one, silently.

**DH-1.3** Both helpers MUST accept `params` as a tuple of positional parameters or `None`, and `None` and an empty
tuple MUST mean the same thing (`*params if params else ()`). Keyword parameters, named parameters and a mapping of
parameters are not part of the contract.

**DH-1.4** Both helpers MUST run on the resource's own held connection, so that a statement issued by a domain
method belongs to that resource's unit of work and to its transaction, and rollup mode still rolls the whole unit of
work back.

**DH-1.5** Both helpers MUST be documented as the way a subclass runs a statement or reads a row, in the module where
they live and on the resource-authoring page.

## 2. The one check

**DH-2.1** `_require_connection()` MUST be the only place in the driver that reads the held connection for a "is it
open" decision, and MUST raise `HandleError("Connection is not open")` when there is none.

**DH-2.2** `begin`, `commit`, `rollback`, `_execute` and `_fetchrow` MUST obtain the connection only through it. The
four copies that exist today (`postgres_resource.py:146`, `:167`, `:182`, `:238`) MUST be gone.

**DH-2.3** The three lifecycle failures MUST keep the wording they have today — `BEGIN failed: …`,
`COMMIT failed: …`, `ROLLBACK failed: …` — so this change does not alter what a lifecycle caller sees.

## 3. The error policy

**DH-3.1** A failure raised by the connection inside a helper MUST be turned into `HandleError` with the driver's
error attached as its `__cause__`, so that a domain method never has to name the driver's exception types and the
driver's own error never reaches the caller raw.

**DH-3.2** The helper MUST use one message: `SQL execution failed: …`. It MUST NOT compose a message that names the
domain operation — the helper does not know it.

**DH-3.3** A domain method that wants its own context MUST wrap deliberately, catching the helper's error and
raising its own with the helper's error as the cause:

```python
try:
    row = await self._fetchrow(query, (showcase_id, showcase_event_id))
except HandleError as error:
    raise HandleError(f"User event read failed: {error}") from error
```

**DH-3.4** The old delegation message of the proxy (`SQL execution error: …`) MUST NOT be reintroduced anywhere: it
belonged to the removed member, and the tests that asserted it are deleted with it.

## 4. What the helpers must not do

| Not this | Why |
| --- | --- |
| Open, commit or roll back a transaction | The unit of work owns the transaction; a helper that managed one would hide it from the domain that must end it |
| Convert a row into a mapping, a dataclass or a domain object | The conversion belongs to the domain boundary; the driver returns what the driver returns |
| Retry, time out or wrap a `CancelledError` | The resource's wait bound and the boundary's lifecycle are `#215`'s, and cancellation must stay cancellation |
| Compose a domain message | The helper has one message, and the domain composes its own |
| Publish itself through `__init__.py` or the package exports | The helpers are the driver's protected surface; `sql/__init__.py` keeps exactly its four exports |

## 5. The helper set is exactly two

**DH-5.1** No other query-shaped helper MAY exist on the driver — no `_fetch` for several rows, no `_fetchval` for a
single value, no `executemany` for many parameter sets.

**DH-5.2** A helper MUST have a caller inside `packages/` at the moment it is added; the two below have one each
after this feature, through the demo's storage primitives. A helper added "for completeness" is a defect of this
contract, not a courtesy.

| Helper | Caller inside `packages/` after this change |
| --- | --- |
| `_execute` | `IdentityStore._write_login` (the statement the domain writes) |
| `_fetchrow` | `IdentityStore._read_person` (the row the domain reads) |

**DH-5.3** Measured, and recorded because the issue assumes otherwise: the repository's dead-code check does **not**
enforce DH-5.2 by itself. `pyproject.toml` sets `[tool.vulture] min_confidence = 80`, an unused method carries 60 %,
and a scratch module with an uncalled private method exits 0 under that setting (and is reported as
`unused method … (60% confidence)` at 60). What the check does catch is an unused import — the `Any` the demo stubs
lose. The rule stands because it is the maintainer's, and the check that shows it is the source search in the closing
task.

## 6. The demo's use of the helpers

**DH-6.1** `IdentityStore` MUST implement the domain's two primitives through the helpers — the read through
`_fetchrow`, the write through `_execute` — and MUST convert the driver's record into a plain mapping at that
boundary, so no domain type above it mentions the driver.

**DH-6.2** A helper call on a resource that was never opened, or that is already closed, MUST surface in the demo as
`HandleError("Connection is not open")`; the base's own `RuntimeError` check that exists today
(`identity_store.py:55-56`) MUST be gone.

**DH-6.3** The examples and the guidance MUST show a domain method built on the helpers, and MUST NOT show a
statement written by an action, by a wrapper or by an in-memory store.
