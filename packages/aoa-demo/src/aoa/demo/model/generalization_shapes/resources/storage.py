# packages/aoa-demo/src/aoa/demo/model/generalization_shapes/resources/storage.py
"""GeneralizationShapesStorage — the store that holds the generalization shapes domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.generalization_shapes.entities.generalization_entities import (
    GeneralizationHeadCoreEntity,
    GeneralizationShapesKindEnumEntity,
    GeneralizationVariantASpecEntity,
    GeneralizationVariantBSpecEntity,
)


@meta(description="Stores the generalization shapes model (stub)")
@entities(
    GeneralizationShapesKindEnumEntity,
    GeneralizationHeadCoreEntity,
    GeneralizationVariantASpecEntity,
    GeneralizationVariantBSpecEntity,
)
class GeneralizationShapesStorage(BaseStorage):
    """Hold the generalization shapes domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
