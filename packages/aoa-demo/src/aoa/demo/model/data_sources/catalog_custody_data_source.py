# packages/aoa-demo/src/aoa/demo/model/data_sources/catalog_custody_data_source.py
"""CatalogCustodyDataSource — the catalog custody store, kept in memory."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource


@meta(description="The catalog custody store, kept in memory")
class CatalogCustodyDataSource(InMemoryDataSource):
    """A demo store kept in the process: the catalog custody domain's rows."""
