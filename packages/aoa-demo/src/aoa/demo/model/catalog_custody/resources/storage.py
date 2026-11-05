# packages/aoa-demo/src/aoa/demo/model/catalog_custody/resources/storage.py
"""CatalogCustodyStorage — the store that holds the catalog custody domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.catalog_custody.catalog_custody_domain import CatalogCustodyDomain


@meta(description="Stores the catalog custody model (stub)", domain=CatalogCustodyDomain)
class CatalogCustodyStorage(BaseStorage):
    """Hold the catalog custody domain's entities; the demo never opens it."""
