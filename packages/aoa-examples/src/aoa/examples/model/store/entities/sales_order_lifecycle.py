# packages/aoa-examples/src/aoa/examples/model/store/entities/sales_order_lifecycle.py
"""Sales-order lifecycle demo (confirmed/rework cycle)."""

from __future__ import annotations

from aoa.action_machine.domain import Lifecycle


class SalesOrderLifecycle(Lifecycle):
    """Demo sales-order lifecycle."""

    _template = (
        Lifecycle()
        .state("new", "New").to("payment_pending", "cancelled").initial()
        .state("payment_pending", "Payment pending").to("confirmed", "cancelled").intermediate()
        .state("confirmed", "Confirmed").to("pending_fulfillment", "rework").intermediate()
        .state("rework", "Rework").to("confirmed").intermediate()
        .state("pending_fulfillment", "Pending fulfillment").to("shipped").intermediate()
        .state("shipped", "Shipped").to("out_for_delivery").intermediate()
        .state("out_for_delivery", "Out for delivery").to("delivered").intermediate()
        .state("delivered", "Delivered").final()
        .state("cancelled", "Cancelled").final()
    )
