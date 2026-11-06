# packages/aoa-demo/src/aoa/demo/model/logistics_mesh/resources/storage.py
"""LogisticsMeshStorage — the store that holds the logistics mesh domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.data_sources.logistics_mesh_data_source import LogisticsMeshDataSource
from aoa.demo.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@meta(description="Stores the logistics mesh model (stub)", domain=LogisticsMeshDomain)
class LogisticsMeshStorage(BaseStorage[LogisticsMeshDataSource]):
    """Hold the logistics mesh domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
