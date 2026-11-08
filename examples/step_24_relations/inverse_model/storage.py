"""Declare the database that holds the cross-module endpoints."""

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage

from .offer import OfferCoreEntity
from .region import RegionCoreEntity


@meta(description="Stores the crossmodule entities")
@entities(
    OfferCoreEntity,
    RegionCoreEntity,
)
class CrossModuleStorage(BaseStorage):
    """Hold the entities of CrossModuleDomain."""
