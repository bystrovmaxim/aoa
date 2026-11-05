# packages/aoa-demo/src/aoa/demo/model/logistics_mesh/resources/storage.py
"""LogisticsMeshStorage — the store that holds the logistics mesh domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@meta(description="Stores the logistics mesh model (stub)", domain=LogisticsMeshDomain)
class LogisticsMeshStorage(BaseStorage):
    """Hold the logistics mesh domain's entities; the demo never opens it."""
