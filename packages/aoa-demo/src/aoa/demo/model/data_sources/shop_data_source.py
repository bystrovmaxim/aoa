# packages/aoa-demo/src/aoa/demo/model/data_sources/shop_data_source.py
"""ShopDataSource — the one database of the storefront, the support desk and inventory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseDataSource


@meta(description="The shop database — storefront, support desk and inventory")
class ShopDataSource(BaseDataSource):
    """A demo database: the resources that name it share one store, and their entities may relate."""
