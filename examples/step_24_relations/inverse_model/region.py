"""Declare the region without importing the offer at runtime."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, Inverse
from aoa.action_machine.intents.entity import entity

from .domain import CrossModuleDomain

if TYPE_CHECKING:
    from .offer import OfferCoreEntity


@entity(description="Region", domain=CrossModuleDomain)
class RegionCoreEntity(BaseCoreEntity):
    """Name the reverse field without a class-valued marker."""

    offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")
