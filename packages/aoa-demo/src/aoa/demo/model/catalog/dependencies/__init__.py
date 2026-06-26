# packages/aoa-demo/src/aoa/demo/model/catalog/dependencies/__init__.py
from aoa.demo.model.catalog.resources.index_sync import IndexSyncClient
from aoa.demo.model.catalog.resources.pricing_feed import PricingFeedClient

__all__ = ["IndexSyncClient", "PricingFeedClient"]
