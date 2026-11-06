# packages/aoa-demo/src/aoa/demo/model/data_sources/__init__.py
"""
The demo's stores: every resource that stores an entity names one of these data sources.

``ShopDataSource`` is one database of three domains — the storefront, the support desk and
inventory — each reaching it through one resource of its own. ``MessagingDataSource`` holds
the outbox and the dead-letter queue, kept by the one resource of the messaging domain. The
rest are a store each: a database of its own (catalog search, the billing warehouse, the
session cache), an external service (the card network, the notification gateway) or a store
kept in memory. A data source belongs to no domain; in the graph it hangs on the application.
"""

from aoa.demo.model.data_sources.catalog_data_source import CatalogDataSource
from aoa.demo.model.data_sources.messaging_data_source import MessagingDataSource
from aoa.demo.model.data_sources.shop_data_source import ShopDataSource

__all__ = ["CatalogDataSource", "MessagingDataSource", "ShopDataSource"]
