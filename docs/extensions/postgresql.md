# PostgreSQL — one connection for one unit of work

[Contents](../index.md) · [Connection ownership](../tutorials/step-17-connections.md)

`PostgresResource` is the PostgreSQL implementation of AOA's SQL resource contract.
One resource holds at most one connection. Create a resource for each call that
needs its own database session; keep the pool at application scope. The resource
does not create a pool or make a shared instance safe for concurrent requests.

If **pool**, **connection**, **unit of work** and **transaction** are new terms, read
[their definitions](../tutorials/step-17-connections.md#four-terms-before-the-first-example)
first. This page builds on that distinction: connection lifetime and transaction
lifetime require separate decisions.

## Installation and construction

```bash
pip install "aoa-action-machine[postgres]"
```

```python
from aoa.action_machine.resources.postgres import PostgresResource

# One connection owned by this resource:
db = PostgresResource({"dsn": "postgresql://user:password@localhost/shop"})

# Alternatively, one connection borrowed from an existing application pool:
db = PostgresResource(pool=pool)
```

These are alternative construction forms. Supply exactly one source. `pool` and
`rollup` are keyword-only arguments. Construction is synchronous and does not
connect; `await db.open()` takes the connection. `await db.close()` releases it.

The SQL resource contract provides `open`, `begin`, `commit`, `rollback` and
`close`, but no public `execute()` method. An action calls a method of its resource,
such as `add_note(text)`. A subclass of `PostgresResource` implements that method
using the protected helpers below. The leading underscore marks methods intended
for resource implementations, rather than direct calls from actions:

- `self._execute(query, params=None)` runs a statement and answers the driver's command
  status, such as `"INSERT 0 1"`. Rows are discarded: adding `RETURNING` to SQL does not
  turn this into a returned row or identifier.
- `self._fetchrow(query, params=None)` runs a query and answers its **first** row, or
  `None`. First, not only: a statement that can match several rows without an ordering
  yields an arbitrary one.

Both check that the connection is open — a resource that never opened, or one already
closed, refuses with `HandleError("Connection is not open")` — and both turn a failure
of the driver into `HandleError("SQL execution failed: …")` with the driver's error
chained as its cause. A method that wants its own message catches that error and raises
its own with the cause attached. A resource that wants a public query surface publishes
one of its own; the framework neither provides nor forbids it.

## How to run these examples

The scripts and notebooks below use the real `PostgresResource` and a small
`RecordingPool`. This replaces only the external connection: it records commands,
limits the number of borrowers and rejects simultaneous use of one connection.
It does not parse SQL, store rows or simulate database isolation. No PostgreSQL
server is required, but the `postgres` extra is needed to import the resource.

Each file is complete and runs independently with `uv run python <path>`. The first
case includes the complete setup below; later blocks show their own `main()` body,
with the complete setup in the linked script and notebook.

## Borrowing does not close the pool

Use the real PostgresResource with a small recording pool. Only the external database connection is replaced.

[Python](../../examples/extensions/postgresql/01_borrow.py) · [Notebook](../../examples/extensions/postgresql/01_borrow.ipynb)

```python
import asyncio
from aoa.action_machine.resources.postgres import PostgresResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.exceptions import HandleError, TransactionLeftOpenError

class RecordingConnection:
    """Record commands; do not parse SQL or simulate database storage."""
    def __init__(self, number):
        """Give this connection a visible identity."""
        self.number = number
        self.commands = []
        self.busy = False
        self.closed = False
    async def execute(self, query, *params):
        """Reject concurrent use and record one command."""
        if self.busy or self.closed:
            raise RuntimeError("connection is busy or closed")
        self.busy = True
        try:
            await asyncio.sleep(0)
            self.commands.append(query)
            return "OK"
        finally:
            self.busy = False
    async def close(self):
        """Mark the physical connection closed."""
        self.closed = True

class RecordingPool:
    """Offer a fixed number of observable connections without a server."""
    def __init__(self, size=1):
        """Create the fixed capacity used by this example."""
        self.connections = [RecordingConnection(i + 1) for i in range(size)]
        self.free = asyncio.Queue()
        for connection in self.connections:
            self.free.put_nowait(connection)
        self.held = set()
        self.closed = False
    async def acquire(self, *, timeout=None):
        """Wait for an available connection with the supplied bound."""
        connection = await asyncio.wait_for(self.free.get(), timeout)
        self.held.add(connection)
        return connection
    async def release(self, connection):
        """Return a borrowed connection exactly once."""
        self.held.remove(connection)
        self.free.put_nowait(connection)
    async def close(self):
        """Close the pool only after all borrowers have returned."""
        assert not self.held
        for connection in self.connections:
            await connection.close()
        self.closed = True


async def main():
    """Run this case and verify its observable result."""
    pool = RecordingPool()
    resource = PostgresResource(pool=pool)
    print("after construction:", len(pool.held))
    await resource.open()
    assert len(pool.held) == 1
    print("after open:", len(pool.held))
    await resource.close()
    assert not pool.held and not pool.closed
    print("after close:", len(pool.held), "pool closed:", pool.closed)
    await pool.close()
    print("after shutdown:", pool.closed)


if __name__ == "__main__":
    asyncio.run(main())
```

Observed output:

```text
after construction: 0
after open: 1
after close: 0 pool closed: False
after shutdown: True
```

Construction takes no connection. open borrows one; close returns it. Only the application closes the pool. The recording pool verifies lifecycle calls, not SQL correctness.

## The pool: one connection per unit of work

A pool is a service-owned object. In a real startup hook, create it with explicit
capacity and close it in the corresponding shutdown path. This configuration
fragment requires a reachable database; the runnable service-lifetime example
uses a recording pool instead.

```python
import os
import asyncpg
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    pool = await asyncpg.create_pool(
        os.environ["APP_POSTGRES_DSN"], min_size=1, max_size=10,
    )
    holder.pool = pool
    try:
        yield
    finally:
        await pool.close()
        holder.pool = None
```

Here `holder` is the application-owned holder defined in the
[complete service example](../../examples/step_17_connections/16_pool_lifespan.ipynb).
Register `PerCallConnection(lambda: NotesResource(pool=holder.require()),
lambda resource: resource.close())` on the route, then pass the hook to
`adapter.build(lifespan=lifespan)`.

The pool's maximum size limits simultaneous borrowers. The resource's
`acquire_timeout` limits waiting for a free connection; the default is 30 seconds.
Override it on a resource subclass when the application's policy differs.
The resource passes it to `pool.acquire(timeout=...)`. A connection-establishment
timeout passed to `create_pool` is not this borrowing timeout. The pool interface
expected by AOA is `PoolProtocol`: acquire an awaitable connection, release it,
and close the pool. The application remains the pool's owner.

The statement examples use this small subclass. `add_note` is the method
called by application code; only its implementation calls `_execute`.

```python
class NotesResource(PostgresResource):
    """The notes domain's resource: its own method runs the statement."""
    async def add_note(self, text: str) -> str:
        """Write one note through the driver's statement helper."""
        return await self._execute("INSERT INTO notes(text) VALUES ($1)", (text,))
```

## Concurrent calls hold different connections

Two calls must overlap to demonstrate isolation. An event holds each call open until both have borrowed.
In this example, `RecordingConnection.calls` records each command together with its
parameters, so the output also shows which note belongs to each connection.

[Python](../../examples/extensions/postgresql/02_concurrent.py) · [Notebook](../../examples/extensions/postgresql/02_concurrent.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
pool = RecordingPool(size=2)
ready = asyncio.Event()
arrivals = []
async def work(label):
    """Hold one resource until the other call has also opened."""
    async with connection_scope({"db": PerCallConnection(
        lambda: NotesResource(pool=pool), lambda resource: resource.close(),
    )}) as connections:
        arrivals.append(label)
        if len(arrivals) == 2:
            ready.set()
        await ready.wait()
        db = connections["db"]
        await db.begin()
        await db.add_note(label)
        await db.commit()
await asyncio.wait_for(asyncio.gather(work("work A"), work("work B")), 2)
for connection in pool.connections:
    assert connection.commands == ["BEGIN", "INSERT INTO notes(text) VALUES ($1)", "COMMIT"]
    print(connection.number, connection.calls)
assert {connection.calls[1][1] for connection in pool.connections} == {("work A",), ("work B",)}
assert not pool.held
print("borrowed after calls:", len(pool.held))
await pool.close()
```

Observed output:

```text
1 [('BEGIN', ()), ('INSERT INTO notes(text) VALUES ($1)', ('work A',)), ('COMMIT', ())]
2 [('BEGIN', ()), ('INSERT INTO notes(text) VALUES ($1)', ('work B',)), ('COMMIT', ())]
borrowed after calls: 0
```

Each command sequence stayed on one connection. Separate sessions prevent one caller from ending the other caller’s transaction. They do not make shared database rows private or remove the need for database concurrency rules.

## An exhausted pool has a bounded wait

The only connection is held by the first resource. A second resource must time out rather than borrow that occupied connection.

[Python](../../examples/extensions/postgresql/03_wait_bound.py) · [Notebook](../../examples/extensions/postgresql/03_wait_bound.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
class QuickResource(PostgresResource):
    """Use a short wait so this failure is quick to reproduce."""
    acquire_timeout = 0.01
pool = RecordingPool()
first = PostgresResource(pool=pool)
second = QuickResource(pool=pool)
await first.open()
try:
    await second.open()
except HandleError as error:
    assert isinstance(error.__cause__, TimeoutError)
    print(type(error).__name__, "caused by", type(error.__cause__).__name__)
else:
    raise AssertionError("The occupied connection was reused")
finally:
    await first.close()
    await second.close()
assert not pool.held
await pool.close()
```

Observed output:

```text
HandleError caused by TimeoutError
```

acquire_timeout bounds waiting for a free pool connection. PostgresResource wraps the pool failure in HandleError and preserves its cause. The pool’s size and the wait duration are different settings.

## A resource can own its connection without a pool

The direct form calls asyncpg.connect in open and the connection’s close in cleanup. Replace only connect so the example needs no database.

[Python](../../examples/extensions/postgresql/08_owned_connection.py) · [Notebook](../../examples/extensions/postgresql/08_owned_connection.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
connection = RecordingConnection(1)
connect = AsyncMock(return_value=connection)
with patch("aoa.action_machine.resources.postgres.postgres_resource.asyncpg.connect", connect):
    db = PostgresResource({"dsn": "postgresql://example.invalid/demo"})
    await db.open()
    await db.close()
connect.assert_awaited_once_with(dsn="postgresql://example.invalid/demo")
assert connection.closed
print("connect calls:", connect.await_count)
print("physical connection closed:", connection.closed)
```

Observed output:

```text
connect calls: 1
physical connection closed: True
```

No network call occurred in this teaching example. In an application, supplying real connection parameters opens a dedicated connection for that resource. Cleanup closes it instead of returning it to a pool.

## Choose exactly one connection source

A resource cannot both borrow and own its connection. Choose one source.

[Python](../../examples/extensions/postgresql/09_both_sources.py) · [Notebook](../../examples/extensions/postgresql/09_both_sources.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
try:
    PostgresResource({"dsn": "example"}, pool=RecordingPool())
except ConnectionValidationError:
    print("ConnectionValidationError")
else:
    raise AssertionError("Invalid construction was accepted")
```

Observed output:

```text
ConnectionValidationError
```

A resource cannot both borrow and own its connection. Choose one source. The check happens during construction, before open and before any database access.

## Choose exactly one connection source

The resource has no implicit default pool or connection settings. Supply one source.

[Python](../../examples/extensions/postgresql/10_no_source.py) · [Notebook](../../examples/extensions/postgresql/10_no_source.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
try:
    PostgresResource()
except ConnectionValidationError:
    print("ConnectionValidationError")
else:
    raise AssertionError("Invalid construction was accepted")
```

Observed output:

```text
ConnectionValidationError
```

The resource has no implicit default pool or connection settings. Supply one source. The check happens during construction, before open and before any database access.

## Open and close can be called again safely

Repeated open keeps the held connection; repeated close does not return it twice. A closed resource can then be opened again.

[Python](../../examples/extensions/postgresql/11_repeat_lifecycle.py) · [Notebook](../../examples/extensions/postgresql/11_repeat_lifecycle.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
pool = RecordingPool()
db = PostgresResource(pool=pool)
await db.open()
await db.open()
assert len(pool.held) == 1
print("after two opens:", len(pool.held))
await db.close()
await db.close()
assert not pool.held
print("after two closes:", len(pool.held))
await db.open()
await db.close()
print("reopened and closed:", len(pool.held))
await pool.close()
```

Observed output:

```text
after two opens: 1
after two closes: 0
reopened and closed: 0
```

This makes cleanup safe for an unopened or already closed resource. It does not make a single open resource safe for concurrent callers.

## Transactions belong inside the connection lifetime

`connection_scope` does not decide whether work should commit. The code that begins
a transaction must finish it before the resource is closed. Its connection stays
held across all statements, including BEGIN, COMMIT and ROLLBACK.

## Explicit commit completes the transaction

Opening a resource does not begin a transaction. Start and finish the transaction explicitly inside the call.

[Python](../../examples/extensions/postgresql/04_commit.py) · [Notebook](../../examples/extensions/postgresql/04_commit.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
pool = RecordingPool()
async with connection_scope({"db": PerCallConnection(lambda: NotesResource(pool=pool), lambda resource: resource.close())}) as connections:
    db = connections["db"]
    await db.begin()
    await db.add_note("hello")
    await db.commit()
assert pool.connections[0].commands == ["BEGIN", "INSERT INTO notes(text) VALUES ($1)", "COMMIT"]
print(pool.connections[0].commands)
print("borrowed:", len(pool.held))
await pool.close()
```

Observed output:

```text
['BEGIN', 'INSERT INTO notes(text) VALUES ($1)', 'COMMIT']
borrowed: 0
```

The scope handles acquisition and release. The transaction owner handles BEGIN and COMMIT. The domain method answers with the driver’s command status, which the recording connection returns as OK; rows are not involved.

## A work failure ends its transaction explicitly

The transaction owner catches a work failure, rolls back, then lets the original error propagate.

[Python](../../examples/extensions/postgresql/05_rollback.py) · [Notebook](../../examples/extensions/postgresql/05_rollback.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
pool = RecordingPool()
try:
    async with connection_scope({"db": PerCallConnection(lambda: NotesResource(pool=pool), lambda resource: resource.close())}) as connections:
        db = connections["db"]
        await db.begin()
        try:
            await db.add_note("work")
            raise ValueError("cannot finish")
        except BaseException:
            await db.rollback()
            raise
except ValueError as error:
    print(str(error))
assert pool.connections[0].commands == ["BEGIN", "INSERT INTO notes(text) VALUES ($1)", "ROLLBACK"]
assert not pool.held
print(pool.connections[0].commands)
await pool.close()
```

Observed output:

```text
cannot finish
['BEGIN', 'INSERT INTO notes(text) VALUES ($1)', 'ROLLBACK']
```

BaseException also covers cancellation. Here rollback succeeds, so the original work error is preserved and close has no unfinished transaction to report.

## Rollup replaces commit with rollback

Use the normal transaction code, but construct the resource with rollup=True.

[Python](../../examples/extensions/postgresql/07_rollup.py) · [Notebook](../../examples/extensions/postgresql/07_rollup.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
pool = RecordingPool()
async with connection_scope({"db": PerCallConnection(lambda: NotesResource(pool=pool, rollup=True), lambda resource: resource.close())}) as connections:
    db = connections["db"]
    await db.begin()
    await db.add_note("work")
    await db.commit()
assert pool.connections[0].commands == ["BEGIN", "INSERT INTO notes(text) VALUES ($1)", "ROLLBACK"]
print(pool.connections[0].commands)
await pool.close()
```

Observed output:

```text
['BEGIN', 'INSERT INTO notes(text) VALUES ($1)', 'ROLLBACK']
```

The transaction ended through rollback, so cleanup does not report it as unfinished. This affects the explicit SQL transaction; it does not undo HTTP calls, messages, sequence increments or writes outside that transaction.

## Closing with a transaction open

Closing is a final check, not an implicit successful commit. If the resource still
tracks an open transaction, close attempts ROLLBACK, then release (or physical
close in direct mode), and finally raises `TransactionLeftOpenError` when those
steps succeeded. If rollback or release itself fails, an operational error can
escape instead. Never infer successful release merely because cleanup was attempted.

## Closing reports an unfinished transaction

Omit commit and rollback deliberately. This is a programming mistake, even if the call body otherwise succeeded.

[Python](../../examples/extensions/postgresql/06_unfinished_transaction.py) · [Notebook](../../examples/extensions/postgresql/06_unfinished_transaction.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
pool = RecordingPool()
db = PostgresResource(pool=pool)
await db.open()
await db.begin()
try:
    await db.close()
except TransactionLeftOpenError as error:
    print(type(error).__name__)
else:
    raise AssertionError("An unfinished transaction was accepted")
assert pool.connections[0].commands == ["BEGIN", "ROLLBACK"]
assert not pool.held
print(pool.connections[0].commands)
print("borrowed when error is caught:", len(pool.held))
await pool.close()
```

Observed output:

```text
TransactionLeftOpenError
['BEGIN', 'ROLLBACK']
borrowed when error is caught: 0
```

When rollback and release succeed, close first returns the connection and then raises TransactionLeftOpenError. Do not use this emergency rollback as the normal way to end a transaction.

## An unfinished transaction outranks the work error

The body raises while its transaction is still open. Cleanup detects a contract violation.

[Python](../../examples/extensions/postgresql/12_contract_precedence.py) · [Notebook](../../examples/extensions/postgresql/12_contract_precedence.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
pool = RecordingPool()
try:
    async with connection_scope({"db": PerCallConnection(lambda: PostgresResource(pool=pool), lambda resource: resource.close())}) as connections:
        await connections["db"].begin()
        raise ValueError("work failed")
except TransactionLeftOpenError as error:
    assert isinstance(error.__cause__, ValueError)
    print(type(error).__name__, "caused by", type(error.__cause__).__name__)
assert not pool.held
print(pool.connections[0].commands)
await pool.close()
```

Observed output:

```text
TransactionLeftOpenError caused by ValueError
['BEGIN', 'ROLLBACK']
```

Unlike an operational closing failure, a ResourceContractViolationError becomes the primary error. The work failure remains its cause. The repair is to end the transaction on the failure path, as in the explicit rollback example.

## Cancellation remains primary after a contract violation

Cancel a call while its transaction is open. Cleanup must release its connection without turning cancellation into an ordinary error.

[Python](../../examples/extensions/postgresql/13_cancel_precedence.py) · [Notebook](../../examples/extensions/postgresql/13_cancel_precedence.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
pool = RecordingPool()
started = asyncio.Event()
async def work():
    """Wait with an intentionally unfinished transaction."""
    async with connection_scope({"db": PerCallConnection(lambda: PostgresResource(pool=pool), lambda resource: resource.close())}) as connections:
        await connections["db"].begin()
        started.set()
        await asyncio.Event().wait()
task = asyncio.create_task(work())
await started.wait()
task.cancel()
try:
    await task
except asyncio.CancelledError as error:
    assert "TransactionLeftOpenError" in error.__notes__[0]
    print("CancelledError")
    print("contract violation recorded:", "TransactionLeftOpenError" in error.__notes__[0])
assert not pool.held
print(pool.connections[0].commands)
await pool.close()
```

Observed output:

```text
CancelledError
contract violation recorded: True
['BEGIN', 'ROLLBACK']
```

Cancellation wins; the unfinished transaction is recorded in an exception note. The transaction was rolled back and the connection returned in this successful-cleanup path.

## Failed commit leaves cleanup responsible for rollback

The connection rejects COMMIT. A failed commit cannot be treated as a completed transaction.

[Python](../../examples/extensions/postgresql/14_failed_commit.py) · [Notebook](../../examples/extensions/postgresql/14_failed_commit.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
class FailingCommitConnection(RecordingConnection):
    """Fail only the commit command."""
    async def execute(self, query, *params):
        """Record commands and reject commit."""
        if query == "COMMIT":
            self.commands.append(query)
            raise OSError("commit unavailable")
        return await super().execute(query, *params)
pool = RecordingPool()
pool.free.get_nowait()
connection = FailingCommitConnection(1)
pool.connections = [connection]
pool.free.put_nowait(connection)
try:
    async with connection_scope({"db": PerCallConnection(lambda: PostgresResource(pool=pool), lambda resource: resource.close())}) as connections:
        await connections["db"].begin()
        await connections["db"].commit()
except TransactionLeftOpenError as error:
    assert isinstance(error.__cause__, HandleError)
    print(type(error).__name__, "caused by", type(error.__cause__).__name__)
assert connection.commands == ["BEGIN", "COMMIT", "ROLLBACK"]
assert not pool.held
print(connection.commands)
await pool.close()
```

Observed output:

```text
TransactionLeftOpenError caused by HandleError
['BEGIN', 'COMMIT', 'ROLLBACK']
```

The failed COMMIT leaves the transaction flag set. Cleanup rolls back and reports TransactionLeftOpenError, with the commit failure as its cause. This is a failure demonstration, not a guarantee about the outcome of a lost database connection.

## The SQL stack: protocol, manager and wrapper

`ProtocolSqlResource` describes the operations a SQL resource supports.
`SqlResource` is the base class for implementations; its default close does nothing,
which is appropriate only for a subclass that owns no external handle.
`PostgresResource` supplies the actual connection lifetime. `WrapperSqlResource`
gives nested actions a restricted view of that owner.

The wrapper delegates rollup inspection and nothing else, and rejects open, begin,
commit, rollback, close and asynchronous context-manager use with
`TransactionProhibitedError`. It exposes no acquire method and no query member: the
query surface left the contract, so there is nothing for a child to run a statement
with. These are ownership restrictions: a child must not return a connection while its
parent still needs it. A resource that *does* want a child to run one of its own
methods returns its own wrapper class from `get_wrapper_class()`; that wrapper
delegates those methods and keeps every refusal.
See the [separate wrapper examples](../tutorials/step-19-resource.md#a-wrapper-for-nested-operations).

## Migrating an existing declaration

Before, a per-call declaration supplied only a factory. It must now also state
cleanup. Change `PerCallConnection(factory=make_resource)` to
`PerCallConnection(factory=make_resource, finalize=lambda resource: resource.close())`.
If the factory used to return one global PostgreSQL resource, move resource
construction into the factory and keep only the pool global to the application.

Replace a positional rollup argument with `rollup=True`. Choose either
`PostgresResource(connection_params, rollup=True)` or
`PostgresResource(pool=pool, rollup=True)`. Avoid reaching through a resource to close
its private connection: call close on the resource you own. Nested actions must not
call it; their wrapper will refuse.
