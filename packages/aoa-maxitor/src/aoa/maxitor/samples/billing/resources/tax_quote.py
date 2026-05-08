# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/resources/tax_quote.py
"""Tax/pricing stub for ``@depends`` and ``connections`` resource manager."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service import ExternalServiceResource
from aoa.maxitor.samples.billing.domain import BillingDomain


class TaxQuoteService:
    async def rate_for(self, jurisdiction: str) -> float:
        return 0.2


@meta(
    description="Tax quote client for aspects/connections (stub)",
    domain=BillingDomain,
)
class TaxQuoteServiceResource(ExternalServiceResource[TaxQuoteService]):
    pass
