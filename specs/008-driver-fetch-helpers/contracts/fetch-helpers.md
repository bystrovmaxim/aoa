# Contract: the page helper and the value helper

**Feature**: `specs/008-driver-fetch-helpers/spec.md` · **Date**: 2026-10-18

This contract fixes the two members this feature adds to `PostgresResource`. It is normative: the shapes, the two
answers and the two messages are what a domain resource over PostgreSQL is written against, and what the helpers
deliberately do not do is as binding as what they do.

## 1. The members

```python
async def _fetch(self, query: str, params: tuple[Any, ...] | None = None) -> list[Any]: ...
async def _fetchval(self, query: str, params: tuple[Any, ...] | None = None) -> Any: ...
```

They join the existing pair, so the driver offers exactly four protected query members:

```python
async def _execute(self, query: str, params: tuple[Any, ...] | None = None) -> str: ...
async def _fetchrow(self, query: str, params: tuple[Any, ...] | None = None) -> Any: ...
async def _fetch(self, query: str, params: tuple[Any, ...] | None = None) -> list[Any]: ...
async def _fetchval(self, query: str, params: tuple[Any, ...] | None = None) -> Any: ...
```

**FH-1.1** `_fetch` MUST run the query on the resource's held connection through `asyncpg.Connection.fetch` and MUST
return every row the driver answered, in the driver's order. It MUST NOT sort, filter, truncate or convert a row.

**FH-1.2** `_fetch` MUST return `[]` when the query matched nothing. It MUST NOT return `None`, and one row MUST
arrive as a list of one.

**FH-1.3** `_fetchval` MUST run the query through `asyncpg.Connection.fetchval` and MUST return the first value of the
first row — not the row, not a tuple, not a rendering of either.

**FH-1.4** `_fetchval` MUST return `None` when the query matched nothing, and MUST be documented as unable to
distinguish that case from a matched row whose first value is SQL `NULL`. A caller that must distinguish the two uses
`_fetchrow`.

**FH-1.5** `_fetch` MUST be annotated `list[Any]` and `_fetchval` `Any`. No driver type — `asyncpg.Record`,
`asyncpg.Connection` — MUST appear in either signature. The module keeps `from __future__ import annotations`.

**FH-1.6** Both members MUST be documented in the multi-line style of the existing pair: purpose, `Args`, `Returns`,
`Raises`. A one-line docstring is not enough here: they are the extension point (spec FR-010).

**FH-1.7** No further query member MUST appear beside the four: not `_fetchmany`, not `_executemany`, not
`_fetchval_or`, not `_fetchrow_or`.

## 2. The one check

**FH-2.1** Both members MUST obtain the connection only through `_require_connection()`, exactly as `_execute` and
`_fetchrow` do. Neither may read `self._conn` for its own "is it open" decision.

**FH-2.2** On a resource that never opened, and on one closed after opening, both MUST raise
`HandleError("Connection is not open")`. An `AttributeError` MUST NOT reach the caller.

**FH-2.3** `_require_connection`, `_execute`, `_fetchrow` and the lifecycle members MUST keep their current behaviour
and wording. This contract adds members; it does not change the ones beside them.

## 3. The one error

**FH-3.1** A failure raised by the connection inside either new member MUST arrive as
`HandleError(f"SQL execution failed: {e}")` with the driver's error attached as `__cause__`.

**FH-3.2** Neither member MUST introduce message text other than the two messages above and
`Connection is not open`. A domain method that wants context wraps deliberately, as with the existing pair.

**FH-3.3** A `CancelledError` MUST NOT be turned into `HandleError`: it is not a driver failure, and the cleanup that
already exists in the transaction path is unchanged.

## 4. The parameters

**FH-4.1** `params` MUST be a tuple of positional values or `None`, and the call MUST be
`*params if params else ()`, as in the existing pair.

**FH-4.2** `None` and an empty tuple MUST produce the same driver call, with no arguments.

**FH-4.3** A mapping of named parameters is outside the contract. Neither member MUST add a runtime `isinstance`
guard, and neither MUST accept a mapping by forwarding it: the annotation is the boundary, and what a caller gets at
runtime is the driver's complaint, wrapped (spec FR-007 and its clarification answer).

## 5. Where the contract is taught

**FH-5.1** `docs/extensions/postgresql.md` ("Installation and construction") and
`docs/how-to/authoring-resource.md` ("If the implementation uses PostgreSQL") MUST list all four members and MUST
show one worked example: a page through `_fetch`, a count through `_fetchval`.

**FH-5.2** The example MUST state that a count answers a number, and that a domain which must tell "no row" from a
SQL `NULL` uses `_fetchrow` instead.

**FH-5.3** The module documentation of `postgres_resource.py` MUST name the four members in its data-flow diagram,
in the class's AI-CORE `CONTRACT` key, and in the `_execute` docstring's pointer to the read helpers.

## 6. What the contract does not promise

- No ordering: `_fetch` answers in whatever order the driver produced, and the statement owns the ordering.
- No paging: `_fetch` answers every row the statement returned; a bound belongs in the statement.
- No conversion: a row stays the driver's record; mapping it to a plain shape is the domain's choice.
- No transaction: neither member opens, commits or rolls one back.
- No timeout: a query timeout is out of scope for this feature.
