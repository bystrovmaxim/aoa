# packages/aoa-demo/src/aoa/demo/model/inventory/resources/storage.py
"""InventoryStorage — the store that holds the inventory domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.inventory.domain import InventoryDomain


@meta(description="Stores the inventory model (stub)", domain=InventoryDomain)
class InventoryStorage(BaseStorage):
    """Hold the inventory domain's entities; the demo never opens it."""
