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
`@meta(description=...)`, lists the entities of its database with `@entities(...)`, and
implements `get_wrapper_class()`. The metadata and the entity list place it in the graph. The
wrapper method says what a nested action receives: `None` means the object may pass through
directly; a class means the runtime constructs that restricted view around the resource.

`BaseResource` itself does not require open or close. Add them when your
implementation has something to acquire and release. The SQL family defines both;
a SQL resource that owns a real connection must implement meaningful cleanup.

A resource inherits the base of its kind directly — `BaseStorage` for a store of data,
`BaseGateway` for someone else's service, `BaseController` for an object the process owns —
`from aoa.action_machine.resources import BaseStorage, BaseGateway, BaseController`.

## A resource is a database

A resource **is** a database: it lists the entities that lie in it with `@entities(...)`, and
the model names no store anywhere else. An entity names its domain with `@entity(domain=...)`
and no resource ([step 22](step-22-entity.md#name-the-domain-of-an-entity)). A database is
shared by domains, so a resource's `@meta` takes no domain: its domains are the domains of
the entities it lists. Two domains whose data lie in one database share one resource:

```python
# Fragment: `StoreDomain` and `SupportDomain` are defined around it.
@entity(description="Customer order", domain=StoreDomain)
class OrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Order identifier")


@entity(description="Support ticket", domain=SupportDomain)
class TicketCoreEntity(BaseCoreEntity):
    id: str = Field(description="Ticket identifier")


@meta(description="The shop database")
@entities(OrderCoreEntity, TicketCoreEntity)
class ShopDatabaseStorage(BaseStorage): ...
```

[Python](../../examples/step_21_resource/08_database_entities.py) · [Notebook](../../examples/step_21_resource/08_database_entities.ipynb)

The graph links the resource to each entity it lists with a `resource_entity` link, and each
entity to its own domain:

```text
schema_version: 2.0
domain: OrderCoreEntity -> StoreDomain
domain: TicketCoreEntity -> SupportDomain
resource_entity: ShopDatabaseStorage -> OrderCoreEntity
resource_entity: ShopDatabaseStorage -> TicketCoreEntity
```

Two databases are two resources, and a relation may join their entities
([step 24](step-24-relations.md#a-relation-joins-entities-of-any-databases)); only an action
glues their data. One entity class may lie in two databases — a replica, a projection — and
then both resources list it. Every kind of resource may declare `@entities`: a gateway lists
the entities the service it calls reports. A resource that never returns an entity may leave
the declaration out.

The declarations are checked when the class is declared:

```text
not an entity: @entities: 'OrderRow' is not an @entity. Every @entities argument must be a class decorated with @entity(description=..., domain=...).
listed twice: @entities: class 'OrderCoreEntity' is listed twice. A database lists each of its entities once.
not a resource: @entities applies only to a resource (a BaseResource subclass); 'ReportBuilder' is not one. A resource is a database, and it lists the entities that lie in it.
a resource with a domain: @meta on ShopDatabaseStorage: a resource is a database shared by domains and takes no domain — its domains are the domains of the entities it lists with @entities. Remove domain=.
```

[Python](../../examples/step_21_resource/09_entities_refusals.py) · [Notebook](../../examples/step_21_resource/09_entities_refusals.ipynb)

How a resource reaches its database is the application's choice, made when it assembles the
resource: a PostgreSQL storage takes a pool opened in the service's lifespan, its own
connection for one script run, or a substitute pool in a test — the same class in all three
([the PostgreSQL page](../extensions/postgresql.md#one-storage-class-three-ways-to-reach-its-database)).
The pool is not part of the model and does not appear in the graph.

### Migrating from data sources

Before #487 the model named where every entity was stored. Each removed name has one replacement:

| Before | After |
|---|---|
| `@entity(description, resource=OrdersStorage)` | `@entity(description, domain=StoreDomain)`; `OrdersStorage` lists the entity with `@entities(...)` |
| `@meta(description, domain=StoreDomain)` on a resource | `@meta(description)`: the resource's domains are its entities' |
| `class ShopDataSource(PostgresDataSource)`, `data_source=shop` | `PostgresPool(dsn, ...)` opened by the application, `pool=pool`; or `connection_params=dsn` |
| `class OrdersStorage(PostgresStorage[ShopDataSource])`, a type argument on any resource base | `class OrdersStorage(PostgresStorage)`: no type argument |
| several resources of one database, one per domain | one resource of that database, listing the entities of every domain kept there |
| `BaseDataSource`, `InMemoryDataSource`, `ExternalServiceDataSource` | nothing: an in-memory store or a service's client is the resource's own business |
| `DataSourceDeclarationError`, `EntityResourceError`, the refusal of `@depends` on another domain's resource | nothing: those rules are gone |
| `entity_resource`, `resource_data_source` and `DataSource` in the graph | `resource_entity` from a resource to each entity it lists (protocol 2.0) |

## A gateway has its own methods

A gateway reaches someone else's service. It is given the service's client when it is built,
keeps it private, and has one method for each thing the domain asks of the service; an aspect
calls those methods and never holds the raw client:

```python
# Fragment: `PaymentClient` is the provider's client; `BillingDomain` is defined around it.


@meta(description="Payment provider")
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

## The machine checks what a resource returns

A resource may answer only with the entities its database holds. The machine checks every
answer: each public method of a resource class — a plain function, a coroutine function or an
async generator whose name does not start with `_` — is wrapped once, when the class is
declared. An action receives the resource itself, not a proxy, so `isinstance`, identity and
attribute access stay as they are, and the check runs however the resource arrived:
`connections[...]`, `box.resolve(...)` or a test substitute. There is no mode that turns it
off. When the model is built, AOA computes a plan for each resource — which of its entities can
reach, through a relation, a class it does not list — so an answer whose classes cannot leave
the list needs only its type checked.

### Listed entities pass unchanged

The examples below share one model: a shop database lists orders, their lines and customers;
an order line points at a product, which lies in the catalog database.

```python
# Fragment: the entities are declared in the linked example.
@meta(description="The shop database")
@entities(OrderCoreEntity, OrderLineCoreEntity, CustomerCoreEntity)
class ShopDatabaseStorage(BaseStorage):
    def get_order(self) -> OrderCoreEntity:
        return make_order()
```

A whole entity, a partial one of a listed class, a list or a mapping of them pass and reach
the caller unchanged. A dictionary member (`BaseEnumEntity`) and a lifecycle state
(`BaseStateEntity`) belong to the model, not to a database: they pass wherever they appear,
without being listed. An answer that carries no entity costs one type check.

```text
whole order: OrderCoreEntity o1
partial order: OrderCoreEntity
list: ['OrderCoreEntity', 'OrderCoreEntity']
mapping: {'c1': 'OrderCoreEntity'}
dictionary member: eur
no entity: 2
```

[Python](../../examples/step_21_resource/10_return_listed.py) · [Notebook](../../examples/step_21_resource/10_return_listed.ipynb)

### An entity the database does not list is refused

An entity whose exact class the list does not name is refused with `ResourceEntitiesError`. The
message names the resource, the method, the place in the answer — attributes by name,
`[index]` in a sequence, `[key]` in a mapping — and the class. A subclass of a listed class is
not listed: a resource returns exactly the classes it promised, and a shorter answer is a
partial entity of the same class. `ResourceEntitiesError` is a `TypeError`, like every refusal
of AOA.

```text
ResourceEntitiesError: ShopDatabaseStorage.get_product returned ProductCoreEntity at answer, which @entities(ShopDatabaseStorage) does not list.
ResourceEntitiesError: ShopDatabaseStorage.list_items returned ProductCoreEntity at answer[1], which @entities(ShopDatabaseStorage) does not list.
ResourceEntitiesError: ShopDatabaseStorage.items_by_kind returned ProductCoreEntity at answer[product], which @entities(ShopDatabaseStorage) does not list.
ResourceEntitiesError: ShopDatabaseStorage.get_gift_order returned GiftOrderCoreEntity at answer, which @entities(ShopDatabaseStorage) does not list.
a TypeError: True
```

[Python](../../examples/step_21_resource/11_return_unlisted.py) · [Notebook](../../examples/step_21_resource/11_return_unlisted.ipynb)

### A relation that leaves the database comes back as a reference

A relation that leads to a class outside the list may be returned only unloaded — a
reference: the relation holds the id and no entity. A loaded entity there is refused, even a
partial one that holds only its id; the product is the catalog's to answer.

```text
reference: p1 loaded: False
get_order_with_product: ShopDatabaseStorage.get_order_with_product returned ProductCoreEntity at answer.lines[0].product, which @entities(ShopDatabaseStorage) does not list.
get_order_with_product_id: ShopDatabaseStorage.get_order_with_product_id returned ProductCoreEntity at answer.lines[0].product, which @entities(ShopDatabaseStorage) does not list.
```

[Python](../../examples/step_21_resource/12_return_reference.py) · [Notebook](../../examples/step_21_resource/12_return_reference.ipynb)

### A stream is checked as it yields

A coroutine is checked when it returns. An async generator is checked element by element: the
caller receives every element before the first one the database does not list, and the refusal
comes at that element. A plain generator, and a plain function that returns an awaitable, are
not checked.

```text
coroutine: OrderCoreEntity
received before the refusal: ['OrderCoreEntity', 'OrderCoreEntity']
ResourceEntitiesError: ShopDatabaseStorage.stream_items returned ProductCoreEntity at answer, which @entities(ShopDatabaseStorage) does not list.
```

[Python](../../examples/step_21_resource/13_return_stream.py) · [Notebook](../../examples/step_21_resource/13_return_stream.ipynb)

### A resource that lists nothing returns no entity

A resource without `@entities` refuses every entity, and the refusal says it declares none; an
empty `@entities()` lists nothing in the same way. A method whose name starts with `_` is the
resource's own business and is not checked, nor are class methods, static methods and
properties.

```text
private helper: OrderCoreEntity
no entity: 1
ResourceEntitiesError: ReportsDatabaseStorage.get_order returned OrderCoreEntity at answer, but ReportsDatabaseStorage declares no @entities.
ResourceEntitiesError: EmptyDatabaseStorage.get_order returned OrderCoreEntity at answer, which @entities(EmptyDatabaseStorage) does not list.
```

[Python](../../examples/step_21_resource/14_return_undeclared.py) · [Notebook](../../examples/step_21_resource/14_return_undeclared.ipynb)

### Each class is checked by its own list

The plan belongs to the class that answered, never to its parent. A subclass with its own
`@entities` is checked by its own list, even in a method it inherits; a subclass that declares
none lists nothing. A gateway is checked the same way as a storage.

```text
register, customer: c1
gateway, product: Tea
ResourceEntitiesError: CustomerRegisterStorage.get_order returned OrderCoreEntity at answer, which @entities(CustomerRegisterStorage) does not list.
ResourceEntitiesError: ShopCopyStorage.get_order returned OrderCoreEntity at answer, but ShopCopyStorage declares no @entities.
ResourceEntitiesError: CatalogGateway.get_customer returned CustomerCoreEntity at answer, which @entities(CatalogGateway) does not list.
```

[Python](../../examples/step_21_resource/15_return_inherited.py) · [Notebook](../../examples/step_21_resource/15_return_inherited.ipynb)

### A wrapper and a test substitute are checked too

A nested action receives the resource's wrapper ([below](#a-wrapper-for-nested-operations));
a wrapper lists nothing of its own, and its answers are checked by the list of the resource it
wraps. A test bench substitute that is a resource instance is checked like the real resource;
a bare `Mock` is not a resource and is not checked.

```text
wrapper: ShopDatabaseStorage.read_product returned ProductCoreEntity at answer, which @entities(ShopDatabaseStorage) does not list.
resource substitute: ShopDatabaseStorage.get_product returned ProductCoreEntity at answer, which @entities(ShopDatabaseStorage) does not list.
bare Mock, not checked: p1
```

[Python](../../examples/step_21_resource/16_return_substitutes.py) · [Notebook](../../examples/step_21_resource/16_return_substitutes.ipynb)

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
from aoa.action_machine.intents.entities import entities

class WarehouseDomain(BaseDomain):
    """Group the inventory example."""
    name = "warehouse"
    description = "Warehouse domain"


# ── Resource: transport only — read and write stock, no decisions ────────────


@meta(description="In-memory inventory store (transport only)")
@entities()
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
owner = ExampleResource(pool=ExamplePool(pool=pool))
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
owner = ExampleResource(pool=ExamplePool(pool=pool))
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
async with connection_scope({"db": PerCallConnection(lambda: NotesStorage(pool=ExamplePool(pool=pool)), lambda resource: resource.close())}) as connections:
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
