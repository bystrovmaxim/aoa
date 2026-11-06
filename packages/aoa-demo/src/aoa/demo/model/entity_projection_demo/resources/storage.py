# packages/aoa-demo/src/aoa/demo/model/entity_projection_demo/resources/storage.py
"""EntityProjectionDemoStorage — the store that holds the entity projection demo domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.data_sources.entity_projection_demo_data_source import EntityProjectionDemoDataSource
from aoa.demo.model.entity_projection_demo.domain import EntityProjectionDemoDomain


@meta(description="Stores the entity projection demo model (stub)", domain=EntityProjectionDemoDomain)
class EntityProjectionDemoStorage(BaseStorage[EntityProjectionDemoDataSource]):
    """Hold the entity projection demo domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
