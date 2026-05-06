# src/maxitor/samples/messaging/entities/outbox_lifecycle.py
"""Lifecycle graph for one outbox row (sample)."""

from action_machine.domain import Lifecycle


class OutboxMessageLifecycle(Lifecycle):
    """Three states: pending → published → consumed."""

    _template = (
        Lifecycle()
        .state("pending", "Pending").to("published").initial()
        .state("published", "Published").to("consumed").intermediate()
        .state("consumed", "Consumed").final()
    )
