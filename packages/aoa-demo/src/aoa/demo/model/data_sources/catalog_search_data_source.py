# packages/aoa-demo/src/aoa/demo/model/data_sources/catalog_search_data_source.py
"""CatalogSearchDataSource — the catalog search index."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseDataSource


@meta(description="The catalog search index")
class CatalogSearchDataSource(BaseDataSource):
    """A demo database apart from the catalog objects: the search index."""
