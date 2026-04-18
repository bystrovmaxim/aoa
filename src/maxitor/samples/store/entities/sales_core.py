# src/maxitor/samples/store/entities/sales_core.py
"""
Клиент, заказ и строка заказа в одном модуле (двусторонний ``Inverse`` между клиентом и заказом).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseEntity,
    CompositeMany,
    Inverse,
    Rel,
    entity,
)
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import (
    CustomerAccountLifecycle,
    SalesOrderLifecycle,
    SalesOrderLineLifecycle,
)


@entity(description="Registered customer", domain=StoreDomain)
class CustomerAccountEntity(BaseEntity):
    lifecycle: CustomerAccountLifecycle = Field(description="Account lifecycle")
    id: str = Field(description="Customer id")
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
    lifecycle: SalesOrderLineLifecycle = Field(description="Line lifecycle")
    id: str = Field(description="Item id")
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
