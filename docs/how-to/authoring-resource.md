# Write a resource with a clear owner

[Contents](../index.md) · [Resource concepts](../tutorials/step-19-resource.md)

Write a resource when an action needs access to a database, an API, a file or another
external system. Put the business decision in the action and the access mechanism
in the resource. Its lifetime is a separate choice: a shared client and a per-call
database session can both be resources.

## Start with the public contract

Subclass `BaseResource`, supply `@meta(description=..., domain=...)`, and implement
`get_wrapper_class()`. Choose the operations your action needs, such as append or
read_stock. BaseResource does not prescribe their names and does not require a
connection lifecycle for a resource that has nothing to acquire.

If the resource does acquire a handle, separate construction from acquisition.
The constructor stores configuration; an asynchronous open acquires the handle;
close releases it. In a per-call declaration, cleanup may run after open fails,
so it must tolerate an absent or partially acquired handle. Closing the resource
must not close a shared application pool or erase the data behind the connection.

The following complete example gives those responsibilities observable behavior.
The list stands in for external storage; no database or transaction is simulated.

## A custom resource releases its handle, not its data

The external storage is represented by a list supplied by the caller. The resource controls access to it for one call.

[Python](../../examples/how_to/06_custom_resource.py) · [Notebook](../../examples/how_to/06_custom_resource.ipynb)

```python
import asyncio
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection

class NotesDomain(BaseDomain):
    """Group the custom resource example."""
    name = "notes"
    description = "Notes transport"

@meta(description="Append notes to a supplied store", domain=NotesDomain)
class NotesResource(BaseResource):
    """Expose storage access with an explicit usable interval."""
    def __init__(self, storage, events):
        """Remember the external storage and lifecycle log."""
        self.storage = storage
        self.events = events
        self.opened = False
    def get_wrapper_class(self):
        """Allow direct use of this non-transactional teaching store."""
        return None
    async def open(self):
        """Make the handle usable."""
        self.opened = True
        self.events.append("open")
    async def append(self, note):
        """Write through the open handle."""
        if not self.opened:
            raise RuntimeError("Resource is not open")
        self.storage.append(note)
        return len(self.storage)
    async def close(self):
        """Release this handle without deleting stored data."""
        self.opened = False
        self.events.append("close")


async def main():
    """Run this case and verify its observable result."""
    storage = []
    events = []
    async with connection_scope({"notes": PerCallConnection(
        lambda: NotesResource(storage, events), lambda resource: resource.close(),
    )}) as connections:
        count = await connections["notes"].append("hello")
        print("written:", count)
    assert storage == ["hello"]
    assert events == ["open", "close"]
    print("stored after close:", storage)
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
```

Observed output:

```text
written: 1
stored after close: ['hello']
['open', 'close']
```

The resource is closed but the data remains in the supplied store. In a real implementation, close releases a connection or file handle; it does not erase the external data. A transactional resource should return a wrapper that also prevents child actions from closing its owner.

## Supply it to an action

An action declares `@connection(NotesResource, key="notes")` and reads
`connections["notes"]`. On a service route, supply the same declaration used in the
example: a factory that constructs NotesResource and a finalizer that calls close.
FastAPI and MCP apply the scope around machine.run. A manual caller must apply it
explicitly, as the example does. [Step 17](../tutorials/step-17-connections.md) shows
both the action and route together.

## Decide what child actions may do

Returning `None` from get_wrapper_class passes the same object to child actions.
This is acceptable only when that access is intended. If the resource owns a
transaction or another handle that children must not close, return a wrapper class
that exposes permitted operations and refuses ownership operations.

For SQL, use the existing `SqlResource` and `WrapperSqlResource` contract instead
of reproducing part of it. The wrapper blocks open, begin, commit, rollback, close
and context-manager use. It still delegates rollup inspection, but has no
`execute()` or other query method. A custom interface needs its own
wrapper, returned from `get_wrapper_class()`, which delegates the domain's own
methods and keeps every refusal. The
[wrapper cases](../tutorials/step-19-resource.md#a-wrapper-for-nested-operations)
show both direct calls and automatic wrapping by box.run.

## If the implementation uses PostgreSQL

Choose `PostgresResource(connection_params, *, rollup=False)` for an owned connection
or `PostgresResource(pool=pool, rollup=False)` for a borrowed one. Never give both
sources or neither. Set acquire_timeout on the concrete resource if the default
30-second borrowing wait is inappropriate. The pool's capacity belongs to its
creation at service startup; the per-call resource never closes it.

The SQL base class has a harmless default close for implementations that hold no
connection. A real connection-owning implementation must override it. For
PostgresResource that implementation already exists, including detection of an
unfinished transaction at close.

Rollup support is also a real obligation. Generic BaseResource refuses it by default.
A SQL implementation must ensure that rollup=True makes commit roll back its explicit
transaction. This is not an all-purpose undo mechanism for external systems.

A subclass of `PostgresResource` can implement its methods using four protected helpers,
one per answer the driver gives. `await self._execute(query, params)` runs a statement and
answers the driver's command status; `await self._fetchrow(query, params)` answers the
query's first row, or `None`; `await self._fetch(query, params)` answers every row in the
driver's order, or `[]`; `await self._fetchval(query, params)` answers the first value of
the first row, or `None`. All four check that the connection is open and turn a failure of
the driver into `HandleError` with the driver's error chained, so the method carries its
business meaning and no transport mechanics. A method that wants its own message catches
that error and raises its own with the cause attached. `SqlResource` does not require an
`execute()` method; the resource defines the public methods its callers need.

```python
async def list_notes(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Return one ordered, bounded page of notes."""
    rows = await self._fetch(
        "SELECT id, text FROM notes ORDER BY id LIMIT $1 OFFSET $2",
        (limit, offset),
    )
    return [dict(row) for row in rows]

async def count_notes(self) -> int:
    """Return how many notes exist, with the helper's ``None`` answered as zero."""
    total = await self._fetchval("SELECT count(*) FROM notes")
    return 0 if total is None else int(total)
```

The page's `ORDER BY` and `LIMIT` are the statement's business, and no match answering
`[]` is what lets the caller iterate without a guard. `_fetchval` cannot tell no row from
a SQL `NULL`: ask `_fetchrow` for the row when the two must be distinguished.
