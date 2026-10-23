# packages/aoa-demo/src/aoa/demo/model/messaging/entities/outbox_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Lifecycle graph for one outbox row (sample)."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class OutboxMessageStateEntity(BaseStateEntity):
    """Status of the OutboxMessage axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    PENDING = value(code="pending", display_name="Pending", sort_order=1)
    PUBLISHED = value(code="published", display_name="Published", sort_order=2)
    CONSUMED = value(code="consumed", display_name="Consumed", sort_order=3)



class OutboxMessageLifecycle(Lifecycle[OutboxMessageStateEntity]):
    """Three states: pending → published → consumed."""


    _template = (
        Lifecycle()
        .state(OutboxMessageStateEntity.PENDING)
        .to(OutboxMessageStateEntity.PUBLISHED)
        .initial()
        .state(OutboxMessageStateEntity.PUBLISHED)
        .to(OutboxMessageStateEntity.CONSUMED)
        .intermediate()
        .state(OutboxMessageStateEntity.CONSUMED)
        .final()
    )
