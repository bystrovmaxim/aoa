# packages/aoa-demo/src/aoa/demo/model/catalog/resources/pricing_feed.py
"""Pricing feed: a stub client and the gateway the domain reaches it through."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway


class PricingFeedClient:
    async def list_price(self, sku: str) -> float:
        return 9.99


@meta(
    description="Pricing feed gateway (stub)",
)
class PricingFeedGateway(BaseGateway):
    """The gateway to the pricing feed: its methods are what the domain asks of it."""

    def __init__(self, client: PricingFeedClient) -> None:
        self._client = client

    async def list_price(self, sku: str) -> float:
        """Ask the pricing feed: list price."""
        return await self._client.list_price(sku)
