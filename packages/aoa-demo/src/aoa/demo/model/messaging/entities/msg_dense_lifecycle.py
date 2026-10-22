# packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_dense_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Lifecycles for expanded messaging / outbox graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class MsgDenseStateEntity(BaseStateEntity):
    """Status of the MsgDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    QUEUED = MsgDenseStateEntity(code="queued", display_name="Queued", sort_order=1)  # noqa: F821
    ROUTED = MsgDenseStateEntity(code="routed", display_name="Routed", sort_order=2)  # noqa: F821
    DRAINED = MsgDenseStateEntity(code="drained", display_name="Drained", sort_order=3)  # noqa: F821



class MsgDenseLifecycle(Lifecycle[MsgDenseStateEntity]):
    """queued → routed → drained."""


    _template = (
        Lifecycle().state(MsgDenseStateEntity.QUEUED).to(MsgDenseStateEntity.ROUTED).initial().state(MsgDenseStateEntity.ROUTED).to(MsgDenseStateEntity.DRAINED).intermediate().state(MsgDenseStateEntity.DRAINED).final()
    )


class MsgWebhookStateEntity(BaseStateEntity):
    """Status of the MsgWebhook axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    RECEIVED = MsgWebhookStateEntity(code="received", display_name="Received", sort_order=1)  # noqa: F821
    VERIFIED = MsgWebhookStateEntity(code="verified", display_name="Verified", sort_order=2)  # noqa: F821



class MsgWebhookLifecycle(Lifecycle[MsgWebhookStateEntity]):
    """received → verified."""


    _template = Lifecycle().state(MsgWebhookStateEntity.RECEIVED).to(MsgWebhookStateEntity.VERIFIED).initial().state(MsgWebhookStateEntity.VERIFIED).final()
