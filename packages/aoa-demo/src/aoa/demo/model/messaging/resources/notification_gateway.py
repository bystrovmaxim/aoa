# packages/aoa-demo/src/aoa/demo/model/messaging/resources/notification_gateway.py
"""Notification service: a stub client and the gateway the domain reaches it through."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway
from aoa.demo.model.data_sources.notification_gateway_data_source import NotificationGatewayDataSource
from aoa.demo.model.messaging.domain import MessagingDomain


class NotificationClient:
    def __init__(self, channel: str = "default") -> None:
        self.channel = channel

    async def send(self, message: str) -> None:
        return None


@meta(
    description="Notification service gateway (stub)",
    domain=MessagingDomain,
)
class NotificationGateway(BaseGateway[NotificationGatewayDataSource]):
    """The gateway to the notification service: its methods are what the domain asks of it."""

    def __init__(self, client: NotificationClient) -> None:
        self._client = client

    async def send(self, message: str) -> None:
        """Ask the notification service: send."""
        return await self._client.send(message)
