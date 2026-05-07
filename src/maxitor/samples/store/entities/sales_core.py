# src/maxitor/samples/store/entities/sales_core.py
"""
Store sales core triangle — mutual ``Inverse`` on three ``BaseEntity`` classes.

``CustomerAccountEntity``, ``SalesOrderEntity``, and ``SalesOrderLineEntity`` share this module because
:class:`~action_machine.domain.relation_markers.Inverse` captures partner types at class-body time,
and importing them from separate modules would circular-import before all three classes exist. Thin
re-export modules (:file:`customer_account.py`, :file:`order_record.py`, :file:`line_item.py`) keep
stable import paths without duplicating declarations.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationMany, AssociationOne, BaseEntity, CompositeMany, Inverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import (
    CustomerAccountLifecycle,
    SalesOrderLifecycle,
    SalesOrderLineLifecycle,
)


@entity(description="Registered customer", domain=StoreDomain)
class CustomerAccountEntity(BaseEntity):
    id: str = Field(description="Customer id")
    lifecycle: CustomerAccountLifecycle = Field(description="Account lifecycle")
    name: str = Field(description="Display name")
    email: str = Field(description="Email")

    orders: Annotated[
        AssociationMany[SalesOrderEntity],
        Inverse(SalesOrderEntity, "customer"),
    ] = Rel(description="Orders")  # type: ignore[assignment]


@entity(description="Customer order", domain=StoreDomain)
class SalesOrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    amount: float = Field(description="Total", ge=0)
    currency: str = Field(default="USD", description="Currency")
    lifecycle: SalesOrderLifecycle = Field(description="Lifecycle")

    customer: Annotated[
        AssociationOne[CustomerAccountEntity],
        Inverse(CustomerAccountEntity, "orders"),
    ] = Rel(description="Customer")  # type: ignore[assignment]

    order_lines: Annotated[
        CompositeMany[SalesOrderLineEntity],
        Inverse(SalesOrderLineEntity, "order"),
    ] = Rel(description="Line items")  # type: ignore[assignment]


@entity(description="Order line", domain=StoreDomain)
class SalesOrderLineEntity(BaseEntity):
    id: str = Field(description="Item id")
    lifecycle: SalesOrderLineLifecycle = Field(description="Line lifecycle")
    product_name: str = Field(description="Product")
    quantity: int = Field(description="Qty", ge=1)
    unit_price: float = Field(description="Unit price", ge=0)

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        Inverse(SalesOrderEntity, "order_lines"),
    ] = Rel(description="Parent order")  # type: ignore[assignment]


CustomerAccountEntity.model_rebuild()
SalesOrderEntity.model_rebuild()
SalesOrderLineEntity.model_rebuild()
