# Contract: the demo's two private reads

**Feature**: `specs/008-driver-fetch-helpers/spec.md` · **Date**: 2026-10-18

This contract fixes the demonstration: the two private reads on the demo's PostgreSQL store that call the new pair.
It exists so that the demonstration cannot quietly become a public API, an action or a route, and so that the
driver-free half of the demo keeps working with no database and no driver extra.

## 1. What is added

```python
class IdentityStore(IdentityStoreBase, PostgresResource):
    async def _list_persons(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]: ...
    async def _count_persons(self) -> int: ...
```

**DR-1.1** `_list_persons` MUST reach the database through `_fetch` and MUST answer a list of plain mappings
(`dict`), so that the driver's record type stops at the store's boundary.

**DR-1.2** `_list_persons` MUST state a deterministic order and a bound in its own statement — `ORDER BY display_name,
id LIMIT $1 OFFSET $2` — and MUST forward `limit` and `offset` as positional parameters.

**DR-1.3** `_count_persons` MUST reach the database through `_fetchval` with a `count(*)` statement and MUST answer
an `int`, treating a `None` answer as `0`.

**DR-1.4** Neither read MUST use `self._conn`, `_require_connection()` or a driver call directly.

## 2. What is not added

**DR-2.1** `IdentityStoreBase` MUST NOT change: it keeps `read_person`, `record_login` and the two abstract
primitives `_read_person`, `_write_login`. No abstract member is added, so no subclass owes a new implementation.

**DR-2.2** `IdentityStoreStub` MUST NOT change: it keeps its two in-memory primitives and gains no page and no count.

**DR-2.3** No action, route, MCP tool or public domain operation MUST be added for the two reads. They are private and
their only caller is the demo's suite.

**DR-2.4** `IdentityStore`'s class-level `@meta` description stays truthful: it describes the domain's operations
(`read a person, record a login`), which are unchanged. If the store's documentation grows a sentence about the two
reads, that sentence names them as storage reads rather than as domain operations.

## 3. The suite

**DR-3.1** `packages/aoa-demo/tests/test_identity_postgres.py`'s `_FakeConnection` MUST gain `fetch` and `fetchval`,
recording `(query, args)` through its existing `_operation` guard, and MUST hold seeded person records.

**DR-3.2** The suite MUST prove: the list read answers mappings, not records; its statement carries the order and the
bound and its parameters arrive positionally; the count read answers an `int`; and both calls are the ones the fake
recorded.

**DR-3.3** Both reads MUST be exercised over the faked pool — the pooled mode the demo documents — and no test MUST
require a live database or the `postgres` extra at import time.

## 4. Why two reads and not a page and a count on the domain

The issue asks the demo domain to call both helpers in its own methods. The maintainer's clarification answered the
"where" question directly: the demo is a shell for building the graph, and what it needs is two private methods for
internal use. A public operation would oblige the driver-free base and the stub to implement it in memory as well,
which doubles the demonstration and changes a package's role from "shows the pattern" to "offers a listing feature".
The two private reads satisfy the rule — each helper has a caller in `packages/` — at the smallest size.
