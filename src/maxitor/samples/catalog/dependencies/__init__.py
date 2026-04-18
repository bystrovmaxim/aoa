# src/maxitor/samples/catalog/dependencies/__init__.py
from maxitor.samples.catalog.dependencies.index_sync import IndexSyncClient
from maxitor.samples.catalog.dependencies.pricing_feed import PricingFeedClient

__all__ = ["IndexSyncClient", "PricingFeedClient"]
