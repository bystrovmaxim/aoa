# packages/aoa-demo/src/aoa/demo/model/generalization_shapes/resources/storage.py
"""GeneralizationShapesStorage — the store that holds the generalization shapes domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.generalization_shapes.generalization_shapes_domain import GeneralizationShapesDomain


@meta(description="Stores the generalization shapes model (stub)", domain=GeneralizationShapesDomain)
class GeneralizationShapesStorage(BaseStorage):
    """Hold the generalization shapes domain's entities; the demo never opens it."""
