# packages/aoa-demo/src/aoa/demo/model/store/entities/sales_order_lifecycle.py
"""Sales-order lifecycle demo (confirmed/rework cycle)."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class SalesOrderStateEntity(BaseStateEntity):
    """Status of the SalesOrder axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class SalesOrderLifecycle(Lifecycle, StateVocabulary):
    """Demo sales-order lifecycle."""

    NEW = SalesOrderStateEntity(code="new", display_name="New", sort_order=1)
    PAYMENT_PENDING = SalesOrderStateEntity(code="payment_pending", display_name="Payment pending", sort_order=2)
    CONFIRMED = SalesOrderStateEntity(code="confirmed", display_name="Confirmed", sort_order=3)
    REWORK = SalesOrderStateEntity(code="rework", display_name="Rework", sort_order=4)
    PENDING_FULFILLMENT = SalesOrderStateEntity(
        code="pending_fulfillment", display_name="Pending fulfillment", sort_order=5
    )
    SHIPPED = SalesOrderStateEntity(code="shipped", display_name="Shipped", sort_order=6)
    OUT_FOR_DELIVERY = SalesOrderStateEntity(code="out_for_delivery", display_name="Out for delivery", sort_order=7)
    DELIVERED = SalesOrderStateEntity(code="delivered", display_name="Delivered", sort_order=8)
    CANCELLED = SalesOrderStateEntity(code="cancelled", display_name="Cancelled", sort_order=9)

    _template = (
        Lifecycle()
        .state(NEW)
        .to(CANCELLED, PAYMENT_PENDING)
        .initial()
        .state(PAYMENT_PENDING)
        .to(CANCELLED, CONFIRMED)
        .intermediate()
        .state(CONFIRMED)
        .to(PENDING_FULFILLMENT, REWORK)
        .intermediate()
        .state(REWORK)
        .to(CONFIRMED)
        .intermediate()
        .state(PENDING_FULFILLMENT)
        .to(SHIPPED)
        .intermediate()
        .state(SHIPPED)
        .to(OUT_FOR_DELIVERY)
        .intermediate()
        .state(OUT_FOR_DELIVERY)
        .to(DELIVERED)
        .intermediate()
        .state(DELIVERED)
        .final()
        .state(CANCELLED)
        .final()
    )
