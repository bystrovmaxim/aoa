# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/resources/pricing_feed.py
"""Pricing feed stub for ``@depends`` and ``connections`` resource manager."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service import ExternalServiceResource
from aoa.maxitor.samples.catalog.domain import CatalogDomain


class PricingFeedClient:
    async def list_price(self, sku: str) -> float:
        return 9.99


@meta(
    description="Pricing feed client for aspects/connections (stub)",
    domain=CatalogDomain,
)
class PricingFeedClientResource(ExternalServiceResource[PricingFeedClient]):
    pass
