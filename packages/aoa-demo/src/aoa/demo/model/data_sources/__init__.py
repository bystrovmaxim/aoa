# packages/aoa-demo/src/aoa/demo/model/data_sources/__init__.py
"""
The demo's databases: each is a data source several of its resources share.

``ShopDataSource`` is one database of three domains — the storefront, the support desk and
inventory — so a support ticket relates to the order and the customer it is about.
``MessagingDataSource`` holds the outbox and the dead-letter queue of one domain, so a replay
ticket relates to the message it replays. ``CatalogDataSource`` is a database with one
resource. Every other demo resource names no data source and keeps its relations to itself.
A data source belongs to no domain; in the graph it hangs on the application.
"""

from aoa.demo.model.data_sources.catalog_data_source import CatalogDataSource
from aoa.demo.model.data_sources.messaging_data_source import MessagingDataSource
from aoa.demo.model.data_sources.shop_data_source import ShopDataSource

__all__ = ["CatalogDataSource", "MessagingDataSource", "ShopDataSource"]
