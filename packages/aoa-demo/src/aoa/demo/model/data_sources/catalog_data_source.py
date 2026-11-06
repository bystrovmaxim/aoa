# packages/aoa-demo/src/aoa/demo/model/data_sources/catalog_data_source.py
"""CatalogDataSource — the catalog object database, a database with one resource."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseDataSource


@meta(description="The catalog object database")
class CatalogDataSource(BaseDataSource):
    """A demo database: the resources that name it share one store, and their entities may relate."""
