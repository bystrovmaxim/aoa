# packages/aoa-demo/src/aoa/demo/model/entity_projection_demo/resources/storage.py
"""EntityProjectionDemoStorage — the store that holds the entity projection demo domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.entity_projection_demo.entities.projection_demo_core import (
    ProjectionDemoCustomerCoreEntity,
    ProjectionDemoOrderCoreEntity,
)


@meta(description="Stores the entity projection demo model (stub)")
@entities(
    ProjectionDemoCustomerCoreEntity,
    ProjectionDemoOrderCoreEntity,
)
class EntityProjectionDemoStorage(BaseStorage):
    """Hold the entity projection demo domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
