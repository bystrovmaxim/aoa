# src/maxitor/test_domain/entities/customer_order.py
"""
Тестовые сущности Customer, Order и OrderItem.

Customer и Order разделить по файлам нельзя: двусторонний ``Inverse`` требует оба класса
при объявлении полей. OrderItem зависит только от Order — объявлен здесь же, чтобы не
плодить цикл ``customer_order`` ↔ ``order_item_entity``.
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
from maxitor.test_domain.domain import TestDomain
from maxitor.test_domain.entities.lifecycle import TestOrderLifecycle


@entity(description="Test customer", domain=TestDomain)
class TestCustomerEntity(BaseEntity):
    id: str = Field(description="Customer id")
    name: str = Field(description="Display name")
    email: str = Field(description="Email")

    orders: Annotated[
        AssociationMany[TestOrderEntity],
        Inverse(TestOrderEntity, "customer"),
    ] = Rel(description="Orders")  # type: ignore[assignment]


@entity(description="Test order", domain=TestDomain)
class TestOrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    amount: float = Field(description="Total", ge=0)
    currency: str = Field(default="USD", description="Currency")
    lifecycle: TestOrderLifecycle = Field(description="Lifecycle")

    customer: Annotated[
        AssociationOne[TestCustomerEntity],
        Inverse(TestCustomerEntity, "orders"),
    ] = Rel(description="Customer")  # type: ignore[assignment]

    order_items: Annotated[
        CompositeMany[TestOrderItemEntity],
        Inverse(TestOrderItemEntity, "order"),
    ] = Rel(description="Line items")  # type: ignore[assignment]


@entity(description="Test order line", domain=TestDomain)
class TestOrderItemEntity(BaseEntity):
    id: str = Field(description="Item id")
    product_name: str = Field(description="Product")
    quantity: int = Field(description="Qty", ge=1)
    unit_price: float = Field(description="Unit price", ge=0)

    order: Annotated[
        AssociationOne[TestOrderEntity],
        Inverse(TestOrderEntity, "order_items"),
    ] = Rel(description="Parent order")  # type: ignore[assignment]


TestCustomerEntity.model_rebuild()
TestOrderEntity.model_rebuild()
TestOrderItemEntity.model_rebuild()
