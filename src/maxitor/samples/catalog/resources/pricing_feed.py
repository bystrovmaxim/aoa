# src/maxitor/samples/catalog/resources/pricing_feed.py
"""Внешний прайсинг (stub) для ``@depends`` и ресурсный менеджер для ``connections``."""

from action_machine.intents.meta import meta
from action_machine.resources.external_service import ExternalServiceResource
from maxitor.samples.catalog.domain import CatalogDomain


class PricingFeedClient:
    async def list_price(self, sku: str) -> float:
        return 9.99


@meta(
    description="Pricing feed client for aspects/connections (stub)",
    domain=CatalogDomain,
)
class PricingFeedClientResource(ExternalServiceResource[PricingFeedClient]):
    pass
