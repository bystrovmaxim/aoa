# packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_device_notice_lifecycle.py
"""Lifecycles for expanded messaging / outbox graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class MsgDeviceNoticeStateEntity(BaseStateEntity):
    """Status of the MsgDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    QUEUED = value(code="queued", display_name="Queued", sort_order=1)
    ROUTED = value(code="routed", display_name="Routed", sort_order=2)
    DRAINED = value(code="drained", display_name="Drained", sort_order=3)


class MsgDeviceNoticeLifecycle(Lifecycle[MsgDeviceNoticeStateEntity]):
    """queued → routed → drained."""

    _template = (
        Lifecycle()
        .state(MsgDeviceNoticeStateEntity.QUEUED)
        .to(MsgDeviceNoticeStateEntity.ROUTED)
        .initial()
        .state(MsgDeviceNoticeStateEntity.ROUTED)
        .to(MsgDeviceNoticeStateEntity.DRAINED)
        .intermediate()
        .state(MsgDeviceNoticeStateEntity.DRAINED)
        .final()
    )
