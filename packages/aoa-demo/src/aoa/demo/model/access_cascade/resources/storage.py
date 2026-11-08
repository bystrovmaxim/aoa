# packages/aoa-demo/src/aoa/demo/model/access_cascade/resources/storage.py
"""AccessCascadeStorage — the store that holds the access cascade domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.access_cascade.entities.cascade_boundary_entity import CascadeBoundaryAssocEntity


@meta(description="Stores the access cascade model (stub)")
@entities(
    CascadeBoundaryAssocEntity,
)
class AccessCascadeStorage(BaseStorage):
    """Hold the access cascade domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
