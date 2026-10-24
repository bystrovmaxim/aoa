# packages/aoa-action-machine/tests/support/complete_relationships/offer.py
"""OfferCoreEntity — one module of the cross-module reciprocal relationship pair.

The reverse class is imported only under ``TYPE_CHECKING``; the postponed annotation names
it as a string, so this module never imports ``region`` at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationMany, BaseCoreEntity, Inverse
from aoa.action_machine.intents.entity import entity

from .domain import CrossDomain

if TYPE_CHECKING:
    from .region import RegionCoreEntity


@entity(description="Offer", domain=CrossDomain)
class OfferCoreEntity(BaseCoreEntity):
    """An offer referenced by many regions."""

    id: str = Field(description="Identifier")
    regions: Annotated[AssociationMany[RegionCoreEntity], Inverse(field_name="offer")] = Field(
        description="Regions associated with this offer"
    )
