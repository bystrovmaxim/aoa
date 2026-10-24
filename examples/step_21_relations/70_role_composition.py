"""Composition: strong ownership pairs only with an association.
Run: .venv/bin/python examples/step_21_relations/70_role_composition.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AggregateOne,
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    CompositeMany,
    CompositeOne,
    Inverse,
)
from aoa.action_machine.domain.exceptions import RoleCompatibilityError
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity


class CompositionDomain(BaseDomain):
    """Group the composition declarations."""

    name = "composition"
    description = "Composition"


@entity(description="Order", domain=CompositionDomain)
class OrderCoreEntity(BaseCoreEntity):
    """An order owns many lines (CompositeMany / AssociationOne)."""

    id: str = Field(description="Order identifier")
    lines: Annotated[CompositeMany[OrderLineCoreEntity], Inverse(field_name="order")] = Field(
        description="Lines owned by this order"
    )


@entity(description="Order line", domain=CompositionDomain)
class OrderLineCoreEntity(BaseCoreEntity):
    """A line's reverse is an association, never another composite."""

    id: str = Field(description="Line identifier")
    order: Annotated[AssociationOne[OrderCoreEntity], Inverse(field_name="lines")] = Field(
        description="Order that owns this line"
    )


@entity(description="Cart", domain=CompositionDomain)
class CartCoreEntity(BaseCoreEntity):
    """A cart owns one checkout (CompositeOne / AssociationMany)."""

    id: str = Field(description="Cart identifier")
    checkout: Annotated[CompositeOne[CheckoutCoreEntity], Inverse(field_name="carts")] = Field(
        description="Checkout owned by this cart"
    )


@entity(description="Checkout", domain=CompositionDomain)
class CheckoutCoreEntity(BaseCoreEntity):
    """Many carts point back through an association."""

    id: str = Field(description="Checkout identifier")
    carts: Annotated[AssociationMany[CartCoreEntity], Inverse(field_name="checkout")] = Field(
        description="Carts that share this checkout"
    )


@entity(description="Composite A", domain=CompositionDomain)
class CompositeACoreEntity(BaseCoreEntity):
    """A composite whose reverse is another composite — refused."""

    id: str = Field(description="Identifier")
    b: Annotated[CompositeOne[CompositeBCoreEntity], Inverse(field_name="a")] = Field(description="Composite B")


@entity(description="Composite B", domain=CompositionDomain)
class CompositeBCoreEntity(BaseCoreEntity):
    """The second composite of the refused pair."""

    id: str = Field(description="Identifier")
    a: Annotated[CompositeMany[CompositeACoreEntity], Inverse(field_name="b")] = Field(description="Composite A")


@entity(description="Composite over aggregate", domain=CompositionDomain)
class CompositeOverAggregateCoreEntity(BaseCoreEntity):
    """A composite paired with an aggregate — refused."""

    id: str = Field(description="Identifier")
    b: Annotated[AggregateOne[AggregateReverseCoreEntity], Inverse(field_name="a")] = Field(description="Aggregate")


@entity(description="Aggregate reverse", domain=CompositionDomain)
class AggregateReverseCoreEntity(BaseCoreEntity):
    """The aggregate side of the refused composite / aggregate pair."""

    id: str = Field(description="Identifier")
    a: Annotated[CompositeMany[CompositeOverAggregateCoreEntity], Inverse(field_name="b")] = Field(
        description="Composite"
    )


@entity(description="Corrected composite", domain=CompositionDomain)
class CorrectedCompositeCoreEntity(BaseCoreEntity):
    """The corrected pair keeps one composite and one association."""

    id: str = Field(description="Identifier")
    b: Annotated[CompositeOne[CorrectedReverseCoreEntity], Inverse(field_name="a")] = Field(description="Reverse")


@entity(description="Corrected reverse", domain=CompositionDomain)
class CorrectedReverseCoreEntity(BaseCoreEntity):
    """The reverse is an association, so the pair is permitted."""

    id: str = Field(description="Identifier")
    a: Annotated[AssociationOne[CorrectedCompositeCoreEntity], Inverse(field_name="b")] = Field(description="Composite")


for model in (
    OrderCoreEntity,
    OrderLineCoreEntity,
    CartCoreEntity,
    CheckoutCoreEntity,
    CompositeACoreEntity,
    CompositeBCoreEntity,
    CompositeOverAggregateCoreEntity,
    AggregateReverseCoreEntity,
    CorrectedCompositeCoreEntity,
    CorrectedReverseCoreEntity,
):
    model.model_rebuild()


def main() -> None:
    """Show the permitted pairs, the two refusals and the corrected pair."""
    assert EntityGraphNode(OrderCoreEntity).node_obj is OrderCoreEntity
    assert EntityGraphNode(CartCoreEntity).node_obj is CartCoreEntity
    assert EntityGraphNode(CorrectedCompositeCoreEntity).node_obj is CorrectedCompositeCoreEntity
    order = OrderCoreEntity(id="order-1", lines=CompositeMany(ids=("line-1", "line-2")))
    assert order.lines.ids == ("line-1", "line-2")
    cart = CartCoreEntity(id="cart-1", checkout=CompositeOne(id="checkout-1"))
    assert cart.checkout.id == "checkout-1"
    try:
        EntityGraphNode(CompositeACoreEntity)
    except RoleCompatibilityError as exc:
        assert (
            str(exc)
            == "Role pair 'CompositeOne' ↔ 'CompositeMany' is not permitted between 'b' on CompositeACoreEntity and 'a' on CompositeBCoreEntity: both endpoints carry ownership roles; the reverse of an ownership endpoint must be AssociationOne or AssociationMany; change one of these two endpoints to an association role according to which side owns the other in your domain."
        )
        print(type(exc).__name__ + ": " + str(exc))
    else:
        raise AssertionError("The prohibited role pair was accepted")
    try:
        EntityGraphNode(CompositeOverAggregateCoreEntity)
    except RoleCompatibilityError as exc:
        assert (
            str(exc)
            == "Role pair 'AggregateOne' ↔ 'CompositeMany' is not permitted between 'b' on CompositeOverAggregateCoreEntity and 'a' on AggregateReverseCoreEntity: both endpoints carry ownership roles; the reverse of an ownership endpoint must be AssociationOne or AssociationMany; change one of these two endpoints to an association role according to which side owns the other in your domain."
        )
        print(type(exc).__name__ + ": " + str(exc))
    else:
        raise AssertionError("The prohibited role pair was accepted")
    print("CompositeMany / AssociationOne: accepted")
    print("CompositeOne / AssociationMany: accepted")
    print("CompositeOne / AssociationOne: accepted")


if __name__ == "__main__":
    main()
