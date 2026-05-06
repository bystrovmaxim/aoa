# src/maxitor/samples/messaging/resources/smtp_transport.py
"""SMTP transport stub for ``@depends`` and ``connections`` resource manager."""

from action_machine.intents.meta import meta
from action_machine.resources.external_service import ExternalServiceResource
from maxitor.samples.messaging.domain import MessagingDomain


class SmtpTransportStub:
    async def send_raw(self, to: str, body: str) -> str:
        return "MSG-ID-SMTP-STUB"


@meta(
    description="SMTP transport client for aspects/connections (stub)",
    domain=MessagingDomain,
)
class SmtpTransportStubResource(ExternalServiceResource[SmtpTransportStub]):
    pass
