# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/resources/webhook_fanout.py
"""Webhook fan-out stub for ``@depends`` and ``connections`` resource manager."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service import ExternalServiceResource
from aoa.maxitor.samples.messaging.domain import MessagingDomain


class WebhookFanoutStub:
    async def post(self, url: str, payload: str) -> int:
        return 202


@meta(
    description="Webhook fan-out client for aspects/connections (stub)",
    domain=MessagingDomain,
)
class WebhookFanoutStubResource(ExternalServiceResource[WebhookFanoutStub]):
    pass
