# Step 17 — Who opens a resource, and who closes it?

[← Complex input](step-16-complex-input.md) · [Contents](../index.md) · [Schema converters →](step-18-converters.md)

An action can declare that it needs a resource with `@connection(..., key="db")`.
Inside the action, `connections["db"]` is the supplied resource. The declaration
states a dependency; it does not open a database connection. Someone outside the
action must supply the object and decide how long it remains usable.

This chapter follows that responsibility from a single HTTP request to a running
service. Start with the two counter examples. Then read about startup and pools.
The error cases have their own [guide](../how-to/connection-lifecycle-failures.md),
so the first working example does not have to explain every failure at once.

## Four terms before the first example

A **resource** is a Python object through which an action accesses storage or another
external system. It may hold a database connection, but those two objects are not
the same thing. A resource may live for one call or be shared, depending on what it owns.

A **connection** is an open session with a database. Statements sent through one
connection use that session, including its current transaction. Sharing one open
connection between overlapping requests can therefore mix their work.

A **pool** keeps reusable connections and lends an available one to a caller.
Several calls can share the pool while holding different connections. Returning a
connection makes it available for reuse; it does not destroy the pool or erase the data.

A **unit of work** here is the interval during which one call owns its resource:
acquire it, do the work, release it. A **transaction** is a database operation begun
with `begin()` and ended with `commit()` or `rollback()`. These intervals are related,
but opening a resource does not automatically start a transaction.

## The two declarations

The `connections=` argument belongs to an individual HTTP route or MCP tool. Each
value is either an existing `BaseResource` or `PerCallConnection(factory, finalize)`.
The action receives the resulting resource, never the declaration object.

With an existing resource, the adapter passes the exact object through. It neither
opens nor closes it. With a per-call declaration, the adapter calls the synchronous
factory, awaits the resource's `open()` if present, runs the action, and then calls
`finalize(resource)`. If the finalizer returns an awaitable, the adapter awaits it.
Both functions are required. Only resources created through this declaration are
managed by this scope.

The first example is complete below. Its resource records lifecycle calls but does
not acquire anything external; this lets us observe the boundary before introducing
a database. `CountAction` increments the supplied counter and returns its value.

## A ready resource is shared

Start with two HTTP calls to one route. The resource is constructed before the route is registered.

[Python](../../examples/step_17_connections/01_connections.py) · [Notebook](../../examples/step_17_connections/01_connections.ipynb)

```python
from aoa.action_machine.model import BaseState
from aoa.action_machine.runtime.tools_box import ToolsBox
import asyncio
from fastapi.testclient import TestClient
from pydantic import Field
from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter

class CounterDomain(BaseDomain):
    """Group this example's resource and action."""
    name = "counter"
    description = "Counter example"

class EmptyParams(BaseParams):
    """No input fields are needed for this case."""

@meta(description="Count calls in memory", domain=CounterDomain)
class CounterResource(BaseResource):
    """Keep a count and record lifecycle events."""
    def __init__(self, events):
        """Start with an empty count."""
        self.count = 0
        self.events = events
    def get_wrapper_class(self):
        """Allow direct use of this in-memory counter."""
        return None
    async def open(self):
        """Record opening without resetting the count."""
        self.events.append("open")
    async def close(self):
        """Record cleanup without acquiring external handles."""
        self.events.append("close")

class CountResult(BaseResult):
    """Expose the count reached by one call."""
    count: int = Field(description="Number of calls seen by this resource")

@meta(description="Increment the supplied counter", domain=CounterDomain)
@check_roles(GuestRole)
@connection(CounterResource, key="counter")
class CountAction(BaseAction[EmptyParams, CountResult]):
    """Increment the supplied resource once."""
    @summary_aspect("Count one call")
    async def count_summary(self, params: EmptyParams, state: BaseState, box: ToolsBox, connections: Connections) -> CountResult:
        """Return the updated count."""
        counter = connections["counter"]
        counter.count += 1
        return CountResult(count=counter.count)


async def main():
    """Run this case and verify its observable result."""
    events = []
    declaration = CounterResource(events)
    app = (FastApiAdapter(machine=ActionProductMachine(loggers=[]),
             auth_coordinator=NoAuthCoordinator(context=Context()))
           .post("/count", CountAction, connections={"counter": declaration})
           .build())
    with TestClient(app) as client:
        responses = [client.post("/count", json={}) for _ in range(2)]
    assert [r.status_code for r in responses] == [200, 200]
    assert [r.json()["count"] for r in responses] == [1, 2]
    for response in responses:
        print(response.json())
    assert events == []
    print("lifecycle:", events)


if __name__ == "__main__":
    asyncio.run(main())
```

Observed output:

```text
{'count': 1}
{'count': 2}
lifecycle: []
```

Both calls received the same counter. The empty lifecycle log proves that the adapter neither opened nor closed the ready resource; its supplier owns its lifetime.

## One resource for each HTTP call

Keep the action unchanged. Replace the ready resource with a factory and a finalizer.

[Python](../../examples/step_17_connections/02_per_call.py) · [Notebook](../../examples/step_17_connections/02_per_call.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
events = []
declaration = PerCallConnection(lambda: CounterResource(events), lambda resource: resource.close())
app = (FastApiAdapter(machine=ActionProductMachine(loggers=[]),
         auth_coordinator=NoAuthCoordinator(context=Context()))
       .post("/count", CountAction, connections={"counter": declaration})
       .build())
with TestClient(app) as client:
    responses = [client.post("/count", json={}) for _ in range(2)]
assert [r.status_code for r in responses] == [200, 200]
assert [r.json()["count"] for r in responses] == [1, 1]
for response in responses:
    print(response.json())
assert events == ['open', 'close', 'open', 'close']
print("lifecycle:", events)
```

Observed output:

```text
{'count': 1}
{'count': 1}
lifecycle: ['open', 'close', 'open', 'close']
```

Each factory call constructed a new counter. The scope opened it before the action and awaited cleanup before returning the response. Newness comes from CounterResource(events), not from the PerCallConnection name.

## What to choose

Use a ready resource when its implementation is designed for shared use and its
owner already manages its lifetime. An in-memory store or a concurrency-safe client
may fit. A raw driver pool is not a `BaseResource`, so it cannot simply be placed
in `connections=`. A resource can instead hold a reference to that pool.

Use a per-call declaration when the resource owns a connection for one caller.
Put the constructor inside `factory`; returning a pre-existing connection-owning
object would apply several callers' lifecycles to the same object. A [separate
counterexample](../../examples/step_17_connections/11_shared_factory.ipynb) demonstrates
that the framework does not detect this mistake.

## A long-lived pool behind a per-call resource

There are two nested lifetimes. The application creates the pool at startup and
closes it at shutdown. During that interval, each call creates a resource, borrows
one connection, uses it, and returns it. The action does not close the pool.

```text
application starts: create pool
    call A: create resource A → borrow connection 1 → work → return connection 1
    call B: create resource B → borrow connection 2 → work → return connection 2
application stops: close pool
```

The calls may overlap. The pool controls how many connections can be borrowed at
once; a caller beyond that limit waits for a free one. A wait timeout controls how
long it may wait. Neither setting replaces the need for a separate resource per call.

A lifespan is an asynchronous context manager. Its code before `yield` performs
startup; execution stays suspended at `yield` while the service runs; the `finally`
block performs shutdown. First observe that lifetime on its own:

## Startup and shutdown belong to the application

The lifespan context manager surrounds the whole running service. Here a log makes its order visible without adding a pool yet.

[Python](../../examples/step_17_connections/14_fastapi_lifespan.py) · [Notebook](../../examples/step_17_connections/14_fastapi_lifespan.ipynb)

Observed output:

```text
['startup']
['startup', 'shutdown']
```

FastApiAdapter passes lifespan to FastAPI. TestClient starts and stops it only when used as a context manager. This is where an application-owned pool belongs.

The pool example uses a **holder**: an ordinary object whose `pool` field is filled
at startup. Its `require()` method returns the pool or raises an explicit error.
The route is registered before startup, but its factory calls `require()` later,
when a request arrives. This timing is why the pool lookup belongs inside the lambda.
The complete example includes the holder, a recording pool, the resource and an action.

## A service pool with a resource for each call

Combine the two lifetimes after learning them separately. The holder makes a pool created at startup available to factories called later.

[Python](../../examples/step_17_connections/16_pool_lifespan.py) · [Notebook](../../examples/step_17_connections/16_pool_lifespan.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
holder = PoolHolder()
created = []
@asynccontextmanager
async def lifespan(app):
    """Own the pool for the whole service lifetime."""
    pool = RecordingPool(size=2)
    holder.pool = pool
    created.append(pool)
    try:
        yield
    finally:
        await pool.close()
        holder.pool = None
app = (FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=NoAuthCoordinator(context=Context()))
    .post("/query", QueryAction, connections={"db": PerCallConnection(
        factory=lambda: NotesResource(pool=holder.require()),
        finalize=lambda resource: resource.close(),
    )}).build(lifespan=lifespan))
with TestClient(app) as client:
    response = client.post("/query", json={})
    assert response.status_code == 200 and response.json() == {"status": "OK"}
    assert not holder.require().held and not holder.require().closed
    print(response.json())
    print("returned after request:", len(holder.require().held) == 0)
assert created[0].closed and holder.pool is None
print("pool closed after shutdown:", created[0].closed)
```

Observed output:

```text
{'status': 'OK'}
returned after request: True
pool closed after shutdown: True
```

The factory calls holder.require at request time, after startup. It creates a new NotesResource, while all calls use the same pool. The finalizer returns this call’s connection; lifespan closes the pool after the service stops. Replace RecordingPool with asyncpg.create_pool for a real database.

## A pool holder reports missing startup

The holder must give a useful error if a factory reaches it before application startup.

[Python](../../examples/step_17_connections/17_holder_before_startup.py) · [Notebook](../../examples/step_17_connections/17_holder_before_startup.ipynb)

Observed output:

```text
Pool is not started
```

A holder is an application object with a checked accessor. The factory reads it after startup; an early read produces an explicit error instead of an accidental attribute error.

## The same in MCP

`McpAdapter.tool(..., connections=...)` uses the same declarations and the same
`connection_scope`. `build(lifespan=...)` passes the server-level lifecycle to
FastMCP. The server framework runs that lifecycle when the server starts and stops;
the adapter does not invent a separate shutdown policy or timeout.

## The same per-call lifecycle for an MCP tool

Call the server in process. The counter action and per-call declaration are the same as for HTTP.

[Python](../../examples/step_17_connections/15_mcp_call.py) · [Notebook](../../examples/step_17_connections/15_mcp_call.ipynb)

Observed output:

```text
{'ok': True, 'code': 'OK', 'data': {'count': 1}}
['startup', 'open', 'close', 'shutdown']
```

The server lifetime surrounds the call lifetime. MCP serializes the result in its own envelope; it does not change which resource is created, opened or finalized.

## What happens around a call

Input parsing and authentication happen before the adapters enter the resource scope.
A request rejected there creates no per-call resource. Once the scope is entered,
it creates and opens resources before `machine.run`, then finalizes them when the
run exits. Response mapping happens after that scope, so mappers must not rely on
an open per-call resource.

A finalizer is called once for each resource the factory actually returned, including
when opening or execution fails. An ordinary exception or task cancellation does
not skip cleanup. This is an attempted cleanup guarantee: a failing finalizer does
not prove that the external connection was returned. Process termination is outside
this mechanism. See [failure cases](../how-to/connection-lifecycle-failures.md).

For a manual call or a custom adapter, use the scope explicitly:

```python
async with connection_scope(declarations) as connections:
    result = await machine.run(context, action, params, connections)
```

Here `declarations` contains ready resources or per-call pairs. The yielded mapping
contains the resources themselves. `machine.run` does not interpret
`PerCallConnection`, and `resolve_connections` only resolves a mapping: it neither
opens nor finalizes it.

## Review your understanding

1. Why can two callers share a pool but not one open PostgreSQL resource?
2. Which function is responsible for returning the connection? Which closes the pool?
3. What changes if the factory returns an existing object?
4. Why does cleanup still need to work when open raises?

Try replacing the per-call counter's factory with one that returns the shared
counter. Predict both responses and the lifecycle log, then run the
[counterexample](../../examples/step_17_connections/11_shared_factory.py).
For actual PostgreSQL construction and transactions, continue with the
[PostgreSQL extension](../extensions/postgresql.md).
