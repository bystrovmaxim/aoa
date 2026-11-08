# packages/aoa-demo/src/aoa/demo/model/messaging/resources/webhook_fanout.py
"""Webhook fan-out: a stub client and the gateway the domain reaches it through."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway


class WebhookFanoutClient:
    async def post(self, url: str, payload: str) -> int:
        return 202


@meta(
    description="Webhook fan-out gateway (stub)",
)
class WebhookFanoutGateway(BaseGateway):
    """The gateway to the webhook fan-out: its methods are what the domain asks of it."""

    def __init__(self, client: WebhookFanoutClient) -> None:
        self._client = client

    async def post(self, url: str, payload: str) -> int:
        """Ask the webhook fan-out: post."""
        return await self._client.post(url, payload)
