# packages/aoa-action-machine/tests/support/complete_relationships/bootstrap.py
"""Composition root: import both declaration modules, resolve, and validate the pair."""

from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses

from .offer import OfferCoreEntity
from .region import RegionCoreEntity


def resolve_and_validate() -> None:
    """Resolve both postponed annotations in this module's namespace, then validate."""
    OfferCoreEntity.model_rebuild(_types_namespace={"RegionCoreEntity": RegionCoreEntity})
    RegionCoreEntity.model_rebuild(_types_namespace={"OfferCoreEntity": OfferCoreEntity})
    validate_entity_inverses([OfferCoreEntity, RegionCoreEntity])
