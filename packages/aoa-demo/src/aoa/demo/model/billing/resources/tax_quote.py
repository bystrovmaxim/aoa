# packages/aoa-demo/src/aoa/demo/model/billing/resources/tax_quote.py
"""Tax/pricing: a stub client and the gateway the domain reaches it through."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway
from aoa.demo.model.billing.domain import BillingDomain


class TaxQuoteClient:
    async def rate_for(self, jurisdiction: str) -> float:
        return 0.2


@meta(
    description="Tax quote gateway (stub)",
    domain=BillingDomain,
)
class TaxQuoteGateway(BaseGateway):
    """The gateway to the tax quote service: its methods are what the domain asks of it."""

    def __init__(self, client: TaxQuoteClient) -> None:
        self._client = client

    async def rate_for(self, jurisdiction: str) -> float:
        """Ask the tax quote service: rate for."""
        return await self._client.rate_for(jurisdiction)
