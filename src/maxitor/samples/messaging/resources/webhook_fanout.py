# src/maxitor/samples/messaging/resources/webhook_fanout.py
"""Фан-аут вебхуков (stub) для ``@depends`` и ресурсный менеджер для ``connections``."""

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.external_service.external_service_resource import (
    ExternalServiceResource,
)
from maxitor.samples.messaging.domain import MessagingDomain


class WebhookFanoutStub:
    async def post(self, url: str, payload: str) -> int:
        return 202


@meta(
    description="Webhook fan-out client for aspects/connections (stub)",
    domain=MessagingDomain,
)
class WebhookFanoutStubResource(ExternalServiceResource[WebhookFanoutStub]):
    pass
