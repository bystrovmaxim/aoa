# packages/aoa-demo/src/aoa/demo/model/data_sources/session_cache_data_source.py
"""SessionCacheDataSource — the storefront session cache."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseDataSource


@meta(description="The storefront session cache")
class SessionCacheDataSource(BaseDataSource):
    """A demo database: the cache that holds storefront sessions."""
