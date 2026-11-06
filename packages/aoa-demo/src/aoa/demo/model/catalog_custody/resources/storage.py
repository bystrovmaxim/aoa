# packages/aoa-demo/src/aoa/demo/model/catalog_custody/resources/storage.py
"""CatalogCustodyStorage — the store that holds the catalog custody domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.catalog_custody.catalog_custody_domain import CatalogCustodyDomain
from aoa.demo.model.data_sources.catalog_custody_data_source import CatalogCustodyDataSource


@meta(description="Stores the catalog custody model (stub)", domain=CatalogCustodyDomain)
class CatalogCustodyStorage(BaseStorage[CatalogCustodyDataSource]):
    """Hold the catalog custody domain's entities; the demo never opens it."""

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
