# packages/aoa-examples/src/aoa/examples/model/store/entities/lifecycle.py
from aoa.action_machine.domain import Lifecycle


class SalesOrderLifecycle(Lifecycle):
    """Demo sales-order lifecycle.

    A **cycle** exists between ``confirmed`` and ``rework`` (two directed transitions).
    In the visualization graph these are two ``LIFECYCLE_TRANSITION`` edges; DAG validation
    does not apply to those edges — the cycle is rendered as-is.

    Extra stages (``payment_pending``, ``pending_fulfillment``, ``out_for_delivery``) stretch
    the happy path for interchange / lifecycle-view demos without removing the cycle.
    """

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


class CustomerAccountLifecycle(Lifecycle):
    """Three states: provisioned → active → closed."""

    _template = (
        Lifecycle()
        .state("provisioned", "Provisioned").to("active").initial()
        .state("active", "Active").to("closed").intermediate()
        .state("closed", "Closed").final()
    )


class SalesOrderLineLifecycle(Lifecycle):
    """Three states: open → reserved → fulfilled."""

    _template = (
        Lifecycle()
        .state("open", "Open").to("reserved").initial()
        .state("reserved", "Reserved").to("fulfilled").intermediate()
        .state("fulfilled", "Fulfilled").final()
    )


class AuditLogEntryLifecycle(Lifecycle):
    """Three states: written → indexed → retained."""

    _template = (
        Lifecycle()
        .state("written", "Written").to("indexed").initial()
        .state("indexed", "Indexed").to("retained").intermediate()
        .state("retained", "Retained").final()
    )


class StoreDualEntryLifecycle(Lifecycle):
    """Demo lifecycle with **two** initial states (online vs walk-in), converging to one path."""

    _template = (
        Lifecycle()
        .state("online_draft", "Online draft").to("active").initial()
        .state("walk_in_quote", "Walk-in quote").to("active").initial()
        .state("active", "Active").to("fulfilled").intermediate()
        .state("fulfilled", "Fulfilled").final()
    )
