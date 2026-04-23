# src/maxitor/samples/billing/resources/ledger_archive.py
"""Заглушка бухгалтерского журнала для ``@depends`` и ресурсный менеджер для ``connections``."""

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.external_service.external_service_resource import (
    ExternalServiceResource,
)
from maxitor.samples.billing.domain import BillingDomain


class LedgerArchiveService:
    async def append(self, event_type: str, payload: str) -> str:
        return "LEDGER-ROW-1"


@meta(
    description="Ledger archive client for aspects/connections (stub)",
    domain=BillingDomain,
)
class LedgerArchiveServiceResource(ExternalServiceResource[LedgerArchiveService]):
    pass
