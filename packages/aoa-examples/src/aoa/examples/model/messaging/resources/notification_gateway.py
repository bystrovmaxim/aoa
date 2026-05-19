# packages/aoa-examples/src/aoa/examples/model/messaging/resources/notification_gateway.py
"""Notification client stub for ``@depends`` and ``connections`` resource manager."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service import ExternalServiceResource
from aoa.examples.model.messaging.domain import MessagingDomain


class NotificationGateway:
    def __init__(self, channel: str = "default") -> None:
        self.channel = channel

    async def send(self, message: str) -> None:
        return None


@meta(
    description="Notification gateway client for aspects/connections (stub)",
    domain=MessagingDomain,
)
class NotificationGatewayResource(ExternalServiceResource[NotificationGateway]):
    pass
