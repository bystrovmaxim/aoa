"""Declare the offer without importing the region at runtime."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationMany, BaseCoreEntity, Inverse
from aoa.action_machine.intents.entity import entity

from .domain import CrossModuleDomain

if TYPE_CHECKING:
    from .region import RegionCoreEntity


@entity(description="Offer", domain=CrossModuleDomain)
class OfferCoreEntity(BaseCoreEntity):
    """Collect the opposite endpoint through a forward reference."""

    regions: Annotated[AssociationMany[RegionCoreEntity], Inverse(field_name="offer")] = Field(description="Regions")
