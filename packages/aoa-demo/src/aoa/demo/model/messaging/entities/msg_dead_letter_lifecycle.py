# packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_dead_letter_lifecycle.py
"""Lifecycles for expanded messaging / outbox graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class MsgDeadLetterStateEntity(BaseStateEntity):
    """Status of the MsgDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    QUEUED = value(code="queued", display_name="Queued", sort_order=1)
    ROUTED = value(code="routed", display_name="Routed", sort_order=2)
    DRAINED = value(code="drained", display_name="Drained", sort_order=3)


class MsgDeadLetterLifecycle(Lifecycle[MsgDeadLetterStateEntity]):
    """queued → routed → drained."""

    _template = (
        Lifecycle()
        .state(MsgDeadLetterStateEntity.QUEUED)
        .to(MsgDeadLetterStateEntity.ROUTED)
        .initial()
        .state(MsgDeadLetterStateEntity.ROUTED)
        .to(MsgDeadLetterStateEntity.DRAINED)
        .intermediate()
        .state(MsgDeadLetterStateEntity.DRAINED)
        .final()
    )
