# Step 21 — Resource: access to the outside world

[← Schema converters](step-20-converters.md) · [Contents](../index.md) · [Entity →](step-22-entity.md)

An action describes what the application is trying to do. A resource supplies the
means to read or change an external system: a database, an API, a queue or a file.
For example, reserving stock involves both a decision and data access. The action
decides whether the requested quantity may be reserved. The resource reads the
current quantity and performs the storage operation.

This distinction is about responsibility, not duration. A resource may exist for
one request and own one connection. A different resource may wrap a shared client
for the life of the service. Calling every resource “long-lived” would hide the
per-call ownership introduced in [Step 19](step-19-connections.md).

## The BaseResource contract

A concrete resource participating in the model supplies metadata with
`@meta(description=..., domain=...)` and implements `get_wrapper_class()`.
The metadata places it in the domain graph. The wrapper method says what a nested
action receives: `None` means the object may pass through directly; a class means
the runtime constructs that restricted view around the resource.

`BaseResource` itself does not require open or close. Add them when your
implementation has something to acquire and release. The SQL family defines both;
a SQL resource that owns a real connection must implement meaningful cleanup.

A resource is also where entities live. Every entity names the one resource that stores it, with
`@entity(resource=...)`, and takes its domain from the resource's `@meta`: a storage holds rows,
a gateway the records an outside service reports, a controller the state it keeps. The kinds are
exported together — `from aoa.action_machine.resources import BaseStorage, BaseGateway, BaseController`.
[Step 22](step-22-entity.md#store-the-entity-in-the-resource-that-holds-it) shows the declaration,
and [step 24](step-24-relations.md#a-relation-joins-entities-of-any-data-sources) why a relation knows no store.

## Resources of one database share a data source

A resource is often a part of a database rather than the whole of it: orders and support
tickets live in one database, each kept by its own resource. A **data source** names that
database — or any other store: an external service, a store kept in memory. It is a primitive
of its own, `BaseDataSource`: a description in `@meta` and no domain, because resources of
several domains may share one store, one resource each. A resource names it as the type
argument of its base, and a resource that stores an entity must name one — it is the entity's
physical place:

```python
# Fragment: the declarations of a model; `StoreDomain` and `SupportDomain` are defined around them.
@meta(description="Main shop database")
class ShopDataSource(BaseDataSource): ...

@meta(description="Orders", domain=StoreDomain)
class OrdersStorage(BaseStorage[ShopDataSource]): ...

@meta(description="Support desk", domain=SupportDomain)
class SupportStorage(BaseStorage[ShopDataSource]): ...
```

A domain reaches a data source through one resource: a second resource of `StoreDomain` on
`ShopDataSource` is refused when the model is built, naming the domain, the data source and
both resources. A resource that stores no entity — a gateway that only calls out — may name
no data source. AOA gives a kind for each store: `PostgresDataSource`, `ExternalServiceDataSource`
(the service's address, credentials and client) and `InMemoryDataSource`. A data source keeps
what its resources share at run time, and the connection parameters live only there:
`PostgresDataSource` holds them and the pool, and a resource built with `data_source=` takes its
connection from it, while the transaction stays the resource's own
([the PostgreSQL page](../extensions/postgresql.md#installation-and-construction)). In the
graph a data source hangs on the application, as a domain does, and each resource that
names it has a `resource_data_source` edge to it.

## A gateway has its own methods

A gateway reaches someone else's service. It is given the service's client when it is built,
keeps it private, and has one method for each thing the domain asks of the service; an aspect
calls those methods and never holds the raw client:

```python
# Fragment: `PaymentClient` is the provider's client; `BillingDomain` is defined around it.
@meta(description="Payment provider", domain=BillingDomain)
class PaymentGateway(BaseGateway):
    def __init__(self, client: PaymentClient) -> None:
        self._client = client

    async def charge(self, amount: float) -> str:
        return await self._client.charge(amount)

    async def refund(self, txn_id: str) -> None:
        await self._client.refund(txn_id)


@depends(PaymentGateway, factory=lambda: PaymentGateway(PaymentClient()))
class SettleInvoiceAction(BaseAction["SettleInvoiceAction.Params", "SettleInvoiceAction.Result"]):
    @regular_aspect("Capture the payment")
    async def capture_aspect(self, params, state, box, connections):
        gateway = await box.resolve(PaymentGateway)
        return {"txn": await gateway.charge(params.amount)}
```

A test substitutes the gateway around a mock client — `TestBench(mocks={PaymentGateway:
PaymentGateway(AsyncMock(spec=PaymentClient))})` — and the bench resets that client's calls
between runs. A gateway holds no transaction: a nested action gets the same gateway, and a
rollup run refuses it, because a call already made to a service cannot be taken back.

## The resource stores; the action decides

The following complete example is deliberately sequential and in memory. It
teaches the division of responsibilities, not a production stock-reservation
algorithm. Concurrent reservations require an atomic database update or appropriate
locking; separate connections alone do not prevent overselling.

## The action decides; the resource stores

Use an in-memory store so the only topic is the division between storage and the business decision.

[Python](../../examples/step_21_resource/01_resource.py) · [Notebook](../../examples/step_21_resource/01_resource.ipynb)

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
from aoa.action_machine.resources import BaseStorage
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter
from aoa.action_machine.resources import Connections

class WarehouseDomain(BaseDomain):
    """Group the inventory example."""
    name = "warehouse"
    description = "Warehouse domain"


# ── Resource: transport only — read and write stock, no decisions ────────────
@meta(description="In-memory inventory store (transport only)", domain=WarehouseDomain)
class InventoryStorage(BaseStorage):

    """Read and update the supplied inventory."""
    def __init__(self, stock: dict[str, int] | None = None) -> None:
        """Initialize this example object."""
        self._stock: dict[str, int] = dict(stock or {})

    @classmethod

    def get_wrapper_class(cls) -> type[BaseStorage] | None:
        """Choose the view supplied to child actions."""
        return None  # in-memory: direct pass-through; a SQL resource would return a wrapper

    async def get_stock(self, sku: str) -> int:
        """Read the available quantity."""
        return self._stock.get(sku, 0)

    async def take(self, sku: str, qty: int) -> None:
        """Subtract the supplied quantity."""
        self._stock[sku] = self._stock.get(sku, 0) - qty


class ReserveParams(BaseParams):
    """Describe the requested reservation."""
    sku: str = Field(description="Product code")
    qty: int = Field(gt=0, description="Quantity to reserve")


class ReserveResult(BaseResult):
    """Report the reservation decision."""
    reserved: bool = Field(description="Whether the reservation succeeded")
    remaining: int = Field(description="Stock left for this SKU")


@meta(description="Reserve stock for a SKU", domain=WarehouseDomain)
@check_roles(GuestRole)
@connection(InventoryStorage, key="inventory")
class ReserveStockAction(BaseAction[ReserveParams, ReserveResult]):

    """Decide whether the requested stock is available."""

    @summary_aspect("Reserve if enough stock")
    async def reserve_summary(self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections) -> ReserveResult:
        """Reserve only when enough stock is available."""
        inventory = connections["inventory"]          # transport, supplied per request
        available = await inventory.get_stock(params.sku)
        # The DECISION lives here, in the Action — not in the Resource.
        if available < params.qty:
            return ReserveResult(reserved=False, remaining=available)
        await inventory.take(params.sku, params.qty)
        return ReserveResult(reserved=True, remaining=available - params.qty)


async def main():
    """Run this case and verify its observable result."""
    inventory = InventoryStorage(stock={"sku-1": 10})
    result = await ActionProductMachine(loggers=[]).run(
        Context(), ReserveStockAction(), ReserveParams(sku="sku-1", qty=3),
        connections={"inventory": inventory},
    )
    assert result.model_dump() == {'reserved': True, 'remaining': 7}
    print(result.model_dump())
    assert await inventory.get_stock("sku-1") == 7


if __name__ == "__main__":
    asyncio.run(main())
```

Observed output:

```text
{'reserved': True, 'remaining': 7}
```

The resource reads and updates stock; ReserveStockAction decides whether the requested quantity is available. This sequential in-memory lesson does not implement concurrent stock reservation; real storage needs an atomic update or suitable locking.

## Insufficient stock is a business refusal

Use an in-memory store so the only topic is the division between storage and the business decision.

[Python](../../examples/step_21_resource/02_refusal.py) · [Notebook](../../examples/step_21_resource/02_refusal.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
inventory = InventoryStorage(stock={"sku-1": 10})
result = await ActionProductMachine(loggers=[]).run(
    Context(), ReserveStockAction(), ReserveParams(sku="sku-1", qty=11),
    connections={"inventory": inventory},
)
assert result.model_dump() == {'reserved': False, 'remaining': 10}
print(result.model_dump())
assert await inventory.get_stock("sku-1") == 10
```

Observed output:

```text
{'reserved': False, 'remaining': 10}
```

The resource reads and updates stock; ReserveStockAction decides whether the requested quantity is available. This sequential in-memory lesson does not implement concurrent stock reservation; real storage needs an atomic update or suitable locking.

## The same action can use an empty store

Use an in-memory store so the only topic is the division between storage and the business decision.

[Python](../../examples/step_21_resource/03_substitution.py) · [Notebook](../../examples/step_21_resource/03_substitution.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
inventory = InventoryStorage(stock={"sku-1": 0})
result = await ActionProductMachine(loggers=[]).run(
    Context(), ReserveStockAction(), ReserveParams(sku="sku-1", qty=1),
    connections={"inventory": inventory},
)
assert result.model_dump() == {'reserved': False, 'remaining': 0}
print(result.model_dump())
assert await inventory.get_stock("sku-1") == 0
```

Observed output:

```text
{'reserved': False, 'remaining': 0}
```

The resource reads and updates stock; ReserveStockAction decides whether the requested quantity is available. This sequential in-memory lesson does not implement concurrent stock reservation; real storage needs an atomic update or suitable locking.

## How an operation gets a resource

With `@connection(ResourceClass, key="inventory")`, the action declares an object
that the caller supplies. An aspect reads it from `connections["inventory"]`.
For a service, the route or tool declares how that object is obtained and finalized.
For a manual `machine.run`, the caller must supply a usable object and manage its
lifetime, optionally through `connection_scope`.

A resource can also be declared with `@depends` and obtained through
`await box.resolve(...)`. That is dependency construction, a separate mechanism
from a route's `PerCallConnection`. Do not assume that choosing a dependency factory
also applies the route's finalizer; choose an explicit owner for external handles.
See [dependencies](step-06-dependencies.md) for that mechanism.

## A wrapper for nested operations

A **nested operation** is an action invoked by another action through `box.run`.
The parent may pass its open resources to the child. The runtime asks each resource
for its wrapper class before passing it on. This allows the child to execute work
without gaining the right to end the parent's transaction or return its connection.

The standard SQL wrapper has no `execute()` or other query method. It still
provides rollup inspection and refuses open, begin, commit, rollback and close
with `TransactionProhibitedError`;
entering or exiting it as an asynchronous context manager is also refused, and it
does not expose acquire. These restrictions apply to the wrapper, not to the resource
owner.

A resource that *does* want a child to run one of its own methods returns its own
wrapper class from `get_wrapper_class()`. That wrapper delegates the domain's methods
and retains the lifecycle restrictions. Returning `None` instead would pass the
resource itself to the child, without those restrictions.

The next two examples construct the wrapper directly to isolate each rule.
They use the recording connection from the PostgreSQL examples, not a live database.
The last example calls `box.run` and verifies that the runtime supplies the wrapper.

## A child cannot close its parent’s connection

The standard wrapper must leave the owner’s connection open.

[Python](../../examples/step_21_resource/05_wrapper_close.py) · [Notebook](../../examples/step_21_resource/05_wrapper_close.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
# Fragment: one part of an example; `RecordingPool` comes from the code around it.
pool = RecordingPool()
owner = ExampleResource(data_source=ExampleDataSource(pool=pool))
await owner.open()
child_view = SqlStorageWrapper(owner)
try:
    await child_view.close()
except TransactionProhibitedError as error:
    print(type(error).__name__)
else:
    raise AssertionError("The wrapper allowed lifecycle control")
assert len(pool.held) == 1
print("owner still holds connection:", len(pool.held) == 1)
await owner.close()
await pool.close()
```

Observed output:

```text
TransactionProhibitedError
owner still holds connection: True
```

The refusal happens before the owner is touched. The parent can continue using the connection and remains responsible for ending its transaction. The outer scope later releases the resource.

## A child cannot enter the owner’s lifecycle

A wrapper grants permission to use a connection, not to manage its lifetime.

[Python](../../examples/step_21_resource/06_wrapper_context.py) · [Notebook](../../examples/step_21_resource/06_wrapper_context.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
# Fragment: one part of an example; `RecordingPool` comes from the code around it.
pool = RecordingPool()
owner = ExampleResource(data_source=ExampleDataSource(pool=pool))
await owner.open()
child_view = SqlStorageWrapper(owner)
try:
    async with child_view:
       raise AssertionError("The context must not open")
except TransactionProhibitedError as error:
    print(type(error).__name__)
else:
    raise AssertionError("The wrapper allowed lifecycle control")
assert len(pool.held) == 1
print("owner still holds connection:", len(pool.held) == 1)
await owner.close()
await pool.close()
```

Observed output:

```text
TransactionProhibitedError
owner still holds connection: True
```

The refusal happens before the owner is touched. The parent can continue using the connection and remains responsible for ending its transaction. The outer scope later releases the resource.

## A real nested action receives a restricted view

Let the machine create the wrapper through `box.run`. The resource provides a wrapper with an `add_note` method. The child writes a note through it, then tries to close the resource and catches `TransactionProhibitedError`.

[Python](../../examples/step_21_resource/07_nested_action.py) · [Notebook](../../examples/step_21_resource/07_nested_action.ipynb)

The resource and its proxy are what this case adds. The resource runs its statement through the driver's helper, and the proxy — the class `get_wrapper_class()` returns — delegates that one method and inherits every refusal:

```python
# Fragment: its imports are left out.
class NotesStorage(PostgresStorage):
    """The domain's resource: its own method, and the proxy it hands a child."""
    async def add_note(self, text: str) -> str:
        """Write one note through the driver's statement helper."""
        return await self._execute("INSERT INTO notes(text) VALUES ($1)", (text,))
    @classmethod
    def get_wrapper_class(cls):
        """A child receives the domain's own proxy, not the default one."""
        return NotesStorageWrapper

@exclude_graph_model
class NotesStorageWrapper(SqlStorageWrapper):
    """The domain's proxy: it delegates its own method and keeps every refusal."""
    @classmethod
    def get_wrapper_class(cls):
        """Keep handing the domain's proxy to a deeper nested action."""
        return NotesStorageWrapper
    async def add_note(self, text: str) -> str:
        """Write a note on the connection its owner holds."""
        return await self._connection_manager.add_note(text)
```

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
# Fragment: one part of an example; `RecordingPool` comes from the code around it.
pool = RecordingPool()
async with connection_scope({"db": PerCallConnection(lambda: NotesStorage(data_source=ExampleDataSource(pool=pool)), lambda resource: resource.close())}) as connections:
    result = await ActionProductMachine(loggers=[]).run(Context(), ParentAction(), EmptyParams(), connections)
    assert result.status == "OK; close refused"
    assert len(pool.held) == 1
    print(result.model_dump())
assert not pool.held
await pool.close()
```

Observed output:

```text
{'status': 'OK; close refused'}
```

The child received a wrapper automatically, and that wrapper is the domain's own: it delegated `add_note`, so the note was written on the connection its parent still holds — and the close that followed was refused. The outer call owned the connection throughout; closing it is the finalizer’s job, after the parent run leaves the scope.

## Rollup and ownership

Rollup means that an explicit SQL transaction executes its work but rolls back at
commit. `PostgresStorage(…, rollup=True)` implements that behavior; a generic
BaseResource does not promise it. It is useful for exercising transactional SQL,
but it does not undo external side effects. See the [isolated rollup example](../../examples/extensions/postgresql/07_rollup.ipynb).

When writing a resource, answer three questions: what access does it provide, who
owns its lifetime, and what may a child do through its wrapper? The answers need
not change the business action. The [authoring guide](../how-to/authoring-resource.md)
turns those decisions into an implementation.

---

[← Schema converters](step-20-converters.md) · [Contents](../index.md) · [Entity →](step-22-entity.md)
