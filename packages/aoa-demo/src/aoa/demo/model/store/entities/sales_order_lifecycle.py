# packages/aoa-demo/src/aoa/demo/model/store/entities/sales_order_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Sales-order lifecycle demo (confirmed/rework cycle)."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class SalesOrderStateEntity(BaseStateEntity):
    """Status of the SalesOrder axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    NEW = value(code="new", display_name="New", sort_order=1)
    PAYMENT_PENDING = value(code="payment_pending", display_name="Payment pending", sort_order=2)
    CONFIRMED = value(code="confirmed", display_name="Confirmed", sort_order=3)
    REWORK = value(code="rework", display_name="Rework", sort_order=4)
    PENDING_FULFILLMENT = value(
        code="pending_fulfillment", display_name="Pending fulfillment", sort_order=5
    )
    SHIPPED = value(code="shipped", display_name="Shipped", sort_order=6)
    OUT_FOR_DELIVERY = value(code="out_for_delivery", display_name="Out for delivery", sort_order=7)
    DELIVERED = value(code="delivered", display_name="Delivered", sort_order=8)
    CANCELLED = value(code="cancelled", display_name="Cancelled", sort_order=9)



class SalesOrderLifecycle(Lifecycle[SalesOrderStateEntity]):
    """Demo sales-order lifecycle."""


    _template = (
        Lifecycle()
        .state(SalesOrderStateEntity.NEW)
        .to(SalesOrderStateEntity.CANCELLED, SalesOrderStateEntity.PAYMENT_PENDING)
        .initial()
        .state(SalesOrderStateEntity.PAYMENT_PENDING)
        .to(SalesOrderStateEntity.CANCELLED, SalesOrderStateEntity.CONFIRMED)
        .intermediate()
        .state(SalesOrderStateEntity.CONFIRMED)
        .to(SalesOrderStateEntity.PENDING_FULFILLMENT, SalesOrderStateEntity.REWORK)
        .intermediate()
        .state(SalesOrderStateEntity.REWORK)
        .to(SalesOrderStateEntity.CONFIRMED)
        .intermediate()
        .state(SalesOrderStateEntity.PENDING_FULFILLMENT)
        .to(SalesOrderStateEntity.SHIPPED)
        .intermediate()
        .state(SalesOrderStateEntity.SHIPPED)
        .to(SalesOrderStateEntity.OUT_FOR_DELIVERY)
        .intermediate()
        .state(SalesOrderStateEntity.OUT_FOR_DELIVERY)
        .to(SalesOrderStateEntity.DELIVERED)
        .intermediate()
        .state(SalesOrderStateEntity.DELIVERED)
        .final()
        .state(SalesOrderStateEntity.CANCELLED)
        .final()
    )
