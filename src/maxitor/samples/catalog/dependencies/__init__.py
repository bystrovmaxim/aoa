# src/maxitor/samples/catalog/dependencies/__init__.py
from maxitor.samples.catalog.resources.index_sync import IndexSyncClient
from maxitor.samples.catalog.resources.pricing_feed import PricingFeedClient

__all__ = ["IndexSyncClient", "PricingFeedClient"]
