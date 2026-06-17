"""
01_relations.py — Entity relations: ownership, Inverse, partial loading

An Entity rarely stands alone: an order has a customer and line items. AOA
declares links with relation containers that carry both cardinality and
ownership meaning:

    CompositeOne / CompositeMany     strong ownership (parts can't exist alone)
    AggregateOne / AggregateMany     weak ownership
    AssociationOne / AssociationMany link without ownership

`Inverse(Target, "field")` names the reverse side so the coordinator can verify
mirroring (types, target, cardinality) when the graph is built — a broken
relation model fails at startup, not half a year later in a report. `NoInverse()`
marks a deliberately one-way link. Every declared edge carries `Rel(description=)`.

Relations load partially like fields: the container always knows the id(s), but
the target row may not be hydrated — reaching through it raises
RelationNotLoadedError, never a silent None.

Tutorial: ../../docs/tutorials/step-21-relations_draft.md  ·  topic: Entity relations

Run:
    uv run python examples/step_21_relations/01_relations.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseEntity,
    CompositeMany,
    Inverse,
    Rel,
    RelationNotLoadedError,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


@entity(description="Customer account", domain=ShopDomain)
class CustomerEntity(BaseEntity):
    id: str = Field(description="Customer id")
    name: str = Field(description="Display name")

    orders: Annotated[
        AssociationMany[OrderEntity],
        Inverse(OrderEntity, "customer"),
    ] = Rel(description="Orders placed by this customer")


@entity(description="Customer order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    total: float = Field(ge=0, description="Order total")

    # association — order and customer exist independently
    customer: Annotated[
        AssociationOne[CustomerEntity],
        Inverse(CustomerEntity, "orders"),
    ] = Rel(description="Customer who placed the order")

    # composition — line items cannot exist without this order
    lines: Annotated[
        CompositeMany[OrderLineEntity],
        Inverse(OrderLineEntity, "order"),
    ] = Rel(description="Line items of the order")


@entity(description="Single line of an order", domain=ShopDomain)
class OrderLineEntity(BaseEntity):
    id: str = Field(description="Line id")
    sku: str = Field(description="Product code")

    order: Annotated[
        AssociationOne[OrderEntity],
        Inverse(OrderEntity, "lines"),
    ] = Rel(description="Parent order")


CustomerEntity.model_rebuild()
OrderEntity.model_rebuild()
OrderLineEntity.model_rebuild()


def main() -> None:
    # 1) Startup check: building the machine builds the graph, which verifies
    #    every Inverse mirrors (types, target, cardinality). A broken relation
    #    model would raise here, not in production.
    ActionProductMachine()
    print("1) Machine built — relation model validated at startup (Inverse mirroring OK)")

    # 2) Id-only relations: the container knows the id, the target isn't hydrated.
    order = OrderEntity(
        id="ord-1",
        total=1500.0,
        customer=AssociationOne[CustomerEntity](id="cust-1"),
        lines=CompositeMany[OrderLineEntity](ids=("line-1", "line-2")),
    )
    print("\n2) Id-only relations:")
    print(f"   order.customer.id  = {order.customer.id}   (is_loaded={order.customer.is_loaded})")
    print(f"   len(order.lines)   = {len(order.lines)}   (is_loaded={order.lines.is_loaded})")
    try:
        _ = order.customer.name        # target row not hydrated
    except RelationNotLoadedError as exc:
        print(f"   order.customer.name -> RelationNotLoadedError: {exc}")
    try:
        _ = list(order.lines)          # many: iteration requires loaded entities
    except RelationNotLoadedError:
        print("   iterating order.lines -> RelationNotLoadedError (ids known, rows not loaded)")

    # 3) Hydrated relation: pass the loaded target entity; attribute access proxies to it.
    customer = CustomerEntity(
        id="cust-1",
        name="Alice",
        orders=AssociationMany[OrderEntity](ids=("ord-1",)),
    )
    order2 = OrderEntity(
        id="ord-2",
        total=99.0,
        customer=AssociationOne[CustomerEntity](id="cust-1", entity=customer),
        lines=CompositeMany[OrderLineEntity](entities=(), entities_loaded=True),
    )
    print("\n3) Hydrated relation:")
    print(f"   order2.customer.name = {order2.customer.name}   (proxied through the loaded entity)")


if __name__ == "__main__":
    main()
