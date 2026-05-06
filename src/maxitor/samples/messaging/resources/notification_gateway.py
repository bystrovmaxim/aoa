# src/maxitor/samples/messaging/resources/notification_gateway.py
"""Клиент уведомлений (заглушка для ``@depends``) и ресурсный менеджер для ``connections``."""

from action_machine.intents.meta import meta
from action_machine.resources.external_service import ExternalServiceResource
from maxitor.samples.messaging.domain import MessagingDomain


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
