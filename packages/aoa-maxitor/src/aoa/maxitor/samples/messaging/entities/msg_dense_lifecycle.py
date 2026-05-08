# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/entities/msg_dense_lifecycle.py
"""Lifecycles for expanded messaging / outbox graph demo."""

from aoa.action_machine.domain import Lifecycle


class MsgDenseLifecycle(Lifecycle):
    """queued → routed → drained."""

    _template = (
        Lifecycle()
        .state("queued", "Queued").to("routed").initial()
        .state("routed", "Routed").to("drained").intermediate()
        .state("drained", "Drained").final()
    )


class MsgWebhookLifecycle(Lifecycle):
    """received → verified."""

    _template = (
        Lifecycle()
        .state("received", "Received").to("verified").initial()
        .state("verified", "Verified").final()
    )
