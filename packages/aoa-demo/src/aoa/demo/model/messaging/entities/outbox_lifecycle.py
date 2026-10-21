# packages/aoa-demo/src/aoa/demo/model/messaging/entities/outbox_lifecycle.py
"""Lifecycle graph for one outbox row (sample)."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class OutboxMessageStateEntity(BaseStateEntity):
    """Status of the OutboxMessage axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class OutboxMessageLifecycle(Lifecycle, StateVocabulary):
    """Three states: pending → published → consumed."""

    PENDING = OutboxMessageStateEntity(code="pending", display_name="Pending", sort_order=1)
    PUBLISHED = OutboxMessageStateEntity(code="published", display_name="Published", sort_order=2)
    CONSUMED = OutboxMessageStateEntity(code="consumed", display_name="Consumed", sort_order=3)

    _template = (
        Lifecycle()
        .state(PENDING)
        .to(PUBLISHED)
        .initial()
        .state(PUBLISHED)
        .to(CONSUMED)
        .intermediate()
        .state(CONSUMED)
        .final()
    )
