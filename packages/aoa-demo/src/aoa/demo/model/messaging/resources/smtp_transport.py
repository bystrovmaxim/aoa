# packages/aoa-demo/src/aoa/demo/model/messaging/resources/smtp_transport.py
"""SMTP transport: a stub client and the gateway the domain reaches it through."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway


class SmtpTransportClient:
    async def send_raw(self, to: str, body: str) -> str:
        return "MSG-ID-SMTP-STUB"


@meta(
    description="SMTP transport gateway (stub)",
)
class SmtpTransportGateway(BaseGateway):
    """The gateway to the SMTP transport: its methods are what the domain asks of it."""

    def __init__(self, client: SmtpTransportClient) -> None:
        self._client = client

    async def send_raw(self, to: str, body: str) -> str:
        """Ask the SMTP transport: send raw."""
        return await self._client.send_raw(to, body)
