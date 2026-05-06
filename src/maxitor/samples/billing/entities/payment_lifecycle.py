# src/maxitor/samples/billing/entities/payment_lifecycle.py
"""Lifecycle graph for payment-event entity (parallel to ``SalesOrderLifecycle`` in store)."""

from action_machine.domain import Lifecycle


class PaymentEventLifecycle(Lifecycle):
    """Three states: recorded → settled → archived."""

    _template = (
        Lifecycle()
        .state("recorded", "Recorded").to("settled").initial()
        .state("settled", "Settled").to("archived").intermediate()
        .state("archived", "Archived").final()
    )
