# packages/aoa-demo/src/aoa/demo/model/messaging/entities/outbox_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Lifecycle graph for one outbox row (sample)."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class OutboxMessageStateEntity(BaseStateEntity):
    """Status of the OutboxMessage axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    PENDING = OutboxMessageStateEntity(code="pending", display_name="Pending", sort_order=1)  # noqa: F821
    PUBLISHED = OutboxMessageStateEntity(code="published", display_name="Published", sort_order=2)  # noqa: F821
    CONSUMED = OutboxMessageStateEntity(code="consumed", display_name="Consumed", sort_order=3)  # noqa: F821



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
