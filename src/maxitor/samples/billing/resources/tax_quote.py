# src/maxitor/samples/billing/resources/tax_quote.py
"""Заглушка налогового/прайсинга для ``@depends`` и ресурсный менеджер для ``connections``."""

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.external_service.external_service_manager import (
    ExternalServiceManager,
)
from maxitor.samples.billing.domain import BillingDomain


class TaxQuoteService:
    async def rate_for(self, jurisdiction: str) -> float:
        return 0.2


@meta(
    description="Tax quote client for aspects/connections (stub)",
    domain=BillingDomain,
)
class TaxQuoteServiceResource(ExternalServiceManager[TaxQuoteService]):
    pass
