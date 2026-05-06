# src/maxitor/samples/store/entities/lifecycle.py
from action_machine.domain import Lifecycle


class SalesOrderLifecycle(Lifecycle):
    """Demo sales-order lifecycle.

    A **cycle** exists between ``confirmed`` and ``rework`` (two directed transitions).
    In the visualization graph these are two ``LIFECYCLE_TRANSITION`` edges; DAG validation
    does not apply to those edges — the cycle is rendered as-is.
    """

    _template = (
        Lifecycle()
        .state("new", "New").to("confirmed", "cancelled").initial()
        .state("confirmed", "Confirmed").to("shipped", "rework").intermediate()
        .state("rework", "Rework").to("confirmed").intermediate()
        .state("shipped", "Shipped").to("delivered").intermediate()
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
