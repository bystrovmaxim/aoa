# src/maxitor/samples/messaging/resources/smtp_transport.py
"""Транспорт SMTP (stub) для ``@depends`` и ресурсный менеджер для ``connections``."""

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.external_service.external_service_manager import (
    ExternalServiceManager,
)
from maxitor.samples.messaging.domain import MessagingDomain


class SmtpTransportStub:
    async def send_raw(self, to: str, body: str) -> str:
        return "MSG-ID-SMTP-STUB"


@meta(
    description="SMTP transport client for aspects/connections (stub)",
    domain=MessagingDomain,
)
class SmtpTransportStubResource(ExternalServiceManager[SmtpTransportStub]):
    pass
