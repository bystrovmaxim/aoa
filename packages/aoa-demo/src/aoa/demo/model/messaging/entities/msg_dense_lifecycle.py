# packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_dense_lifecycle.py
"""Lifecycles for expanded messaging / outbox graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class MsgDenseStateEntity(BaseStateEntity):
    """Status of the MsgDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class MsgDenseLifecycle(Lifecycle, StateVocabulary):
    """queued → routed → drained."""

    QUEUED = MsgDenseStateEntity(code="queued", display_name="Queued", sort_order=1)
    ROUTED = MsgDenseStateEntity(code="routed", display_name="Routed", sort_order=2)
    DRAINED = MsgDenseStateEntity(code="drained", display_name="Drained", sort_order=3)

    _template = (
        Lifecycle().state(QUEUED).to(ROUTED).initial().state(ROUTED).to(DRAINED).intermediate().state(DRAINED).final()
    )


class MsgWebhookStateEntity(BaseStateEntity):
    """Status of the MsgWebhook axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class MsgWebhookLifecycle(Lifecycle, StateVocabulary):
    """received → verified."""

    RECEIVED = MsgWebhookStateEntity(code="received", display_name="Received", sort_order=1)
    VERIFIED = MsgWebhookStateEntity(code="verified", display_name="Verified", sort_order=2)

    _template = Lifecycle().state(RECEIVED).to(VERIFIED).initial().state(VERIFIED).final()
