# packages/aoa-action-machine/tests/support/round_trip_model.py
"""
A model holding every value type AOA gives a JSON form, for the read-back tests of issue #409.

An order points at its customer (One), holds its lines (Many), selects a currency
from a dictionary as a relation and as a bare field, and carries a lifecycle; a
Result holds the order whole, a projection of it and a list of orders.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseStateEntity,
    CompositeOne,
    Lifecycle,
    NoInverse,
    value,
)
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseResult
from aoa.action_machine.resources.base_storage import BaseStorage


class RoundTripDomain(BaseDomain):
    """Domain of the read-back model."""

    name = "round_trip"
    description = "Read-back model"


@entity(description="Customer", domain=RoundTripDomain)
class RtCustomerCoreEntity(BaseCoreEntity):
    """A customer with a UUID id."""

    id: UUID = Field(description="Customer id")
    name: str = Field(description="Name")
    email: str = Field(description="Email")


@entity(description="Order line", domain=RoundTripDomain)
class RtLineCoreEntity(BaseCoreEntity):
    """A line of an order."""

    id: str = Field(description="Line id")
    quantity: int = Field(ge=1, description="Quantity")


@entity(description="Currency", domain=RoundTripDomain)
class RtCurrencyEnumEntity(BaseEnumEntity):
    """A closed catalogue of currencies."""

    symbol: str = Field(default="", description="Symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


@entity(description="Order status", domain=RoundTripDomain)
class RtOrderStateEntity(BaseStateEntity):
    """The statuses of an order."""

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Paid")


class RtOrderLifecycle(Lifecycle[RtOrderStateEntity]):
    """Draft, then paid."""

    _template = (
        Lifecycle()
        .state(RtOrderStateEntity.DRAFT)
        .to(RtOrderStateEntity.PAID)
        .initial()
        .state(RtOrderStateEntity.PAID)
        .final()
    )


@entity(description="Order", domain=RoundTripDomain)
class RtOrderCoreEntity(BaseCoreEntity):
    """An order with every kind of value."""

    id: str = Field(description="Order id")
    total: float = Field(description="Total")
    customer: Annotated[AssociationOne[RtCustomerCoreEntity], NoInverse()] = Field(description="Customer")
    lines: Annotated[AssociationMany[RtLineCoreEntity], NoInverse()] = Field(description="Lines")
    currency: Annotated[CompositeOne[RtCurrencyEnumEntity], NoInverse()] = Field(description="Currency")
    lifecycle: RtOrderLifecycle = Field(description="Lifecycle")


@meta(description="Stores the round trip entities")
@entities(RtCustomerCoreEntity, RtLineCoreEntity, RtOrderCoreEntity)
class RoundTripStorage(BaseStorage):
    """Hold the round trip entities; a dictionary member and a lifecycle state belong to the model, not a database."""


ORDER_SUMMARY = {
    "type": "object",
    "properties": {"id": {"type": "string"}, "total": {"type": "number"}},
    "required": ["id", "total"],
    "additionalProperties": False,
}


class RtOrderResult(BaseResult):
    """A Result holding the order whole, a projection of it, a list and a bare dictionary value."""

    order: RtOrderCoreEntity = Field(description="Order")
    summary: RtOrderCoreEntity.schema(schema=ORDER_SUMMARY) = Field(description="Summary")  # type: ignore[valid-type]
    history: list[RtOrderCoreEntity] = Field(default_factory=list, description="Earlier orders")
    settlement: RtCurrencyEnumEntity = Field(description="Settlement currency")


CUSTOMER_ID = UUID("00000000-0000-0000-0000-000000000001")


def customer() -> RtCustomerCoreEntity:
    """A full customer."""
    return RtCustomerCoreEntity(id=CUSTOMER_ID, name="Ann", email="ann@example.com")


def order(
    *,
    customer_loaded: bool = True,
    lines: tuple[RtLineCoreEntity, ...] | None = (),
    status: str = "paid",
) -> RtOrderCoreEntity:
    """
    An order: the customer loaded (partial, id and name) or not; the lines loaded or not.

    ``lines=None`` leaves the lines not loaded; a tuple, even empty, loads them.
    """
    held = RtCustomerCoreEntity.partial(id=CUSTOMER_ID, name="Ann")
    line_ids = ("l1", "l2") if lines is None else tuple(line.id for line in lines)
    return RtOrderCoreEntity(
        id="o1",
        total=99.5,
        customer=AssociationOne(id=CUSTOMER_ID, entity=held) if customer_loaded else AssociationOne(id=CUSTOMER_ID),
        lines=AssociationMany(ids=line_ids)
        if lines is None
        else AssociationMany(ids=line_ids, entities=lines, entities_loaded=True),
        currency=CompositeOne(id="eur", entity=RtCurrencyEnumEntity.EUR),
        lifecycle=RtOrderLifecycle(status),
    )


def result(
    *,
    customer_loaded: bool = True,
    lines: tuple[RtLineCoreEntity, ...] | None = (),
    status: str = "paid",
) -> RtOrderResult:
    """A Result over one order, its projection, one earlier order and a settlement currency."""
    current = order(customer_loaded=customer_loaded, lines=lines, status=status)
    return RtOrderResult(
        order=current,
        summary=current,
        history=[order(customer_loaded=False, lines=None, status="draft")],
        settlement=RtCurrencyEnumEntity.USD,
    )
