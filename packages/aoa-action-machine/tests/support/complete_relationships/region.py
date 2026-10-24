# packages/aoa-action-machine/tests/support/complete_relationships/region.py
"""RegionCoreEntity — the other module of the cross-module reciprocal relationship pair."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, Inverse
from aoa.action_machine.intents.entity import entity

from .domain import CrossDomain

if TYPE_CHECKING:
    from .offer import OfferCoreEntity


@entity(description="Region", domain=CrossDomain)
class RegionCoreEntity(BaseCoreEntity):
    """A region selecting one offer."""

    id: str = Field(description="Identifier")
    offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(
        description="Offer associated with this region"
    )
