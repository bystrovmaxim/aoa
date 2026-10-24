"""Declare reciprocal pairs and migrate one-sided inverse markers.
Run: .venv/bin/python examples/step_21_relations/65_reciprocal_directions.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationMany, AssociationOne, BaseCoreEntity, Inverse, NoInverse
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
from aoa.action_machine.intents.entity import entity


class DirectionDomain(BaseDomain):
    """Group the direction declarations."""

    name = "directions"
    description = "Reciprocal directions"


@entity(description="Offer", domain=DirectionDomain)
class OfferCoreEntity(BaseCoreEntity):
    """Collect the regions offering this product."""

    regions: Annotated[AssociationMany[RegionCoreEntity], Inverse(field_name="offer")] = Field(description="Regions")


@entity(description="Region", domain=DirectionDomain)
class RegionCoreEntity(BaseCoreEntity):
    """Name the opposite endpoint explicitly."""

    offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")


@entity(description="One-way bookmark", domain=DirectionDomain)
class BookmarkCoreEntity(BaseCoreEntity):
    """Keep an intentional unpaired link."""

    offer: Annotated[AssociationOne[OfferCoreEntity], NoInverse()] = Field(description="Bookmarked offer")


@entity(description="Old reverse endpoint", domain=DirectionDomain)
class OldOfferCoreEntity(BaseCoreEntity):
    """Keep the previous unpaired reverse declaration."""

    regions: Annotated[AssociationMany[OldRegionCoreEntity], NoInverse()] = Field(description="Regions")


@entity(description="Old forward endpoint", domain=DirectionDomain)
class OldRegionCoreEntity(BaseCoreEntity):
    """Demonstrate the one-sided inverse refusal."""

    offer: Annotated[AssociationOne[OldOfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")


for model in (OfferCoreEntity, RegionCoreEntity, OldOfferCoreEntity, OldRegionCoreEntity):
    model.model_rebuild()


def reciprocal_pair() -> None:
    """Validate both endpoints after forward references resolve."""
    validate_entity_fields([OfferCoreEntity, RegionCoreEntity])
    validate_entity_inverses([OfferCoreEntity, RegionCoreEntity])
    offer = OfferCoreEntity(regions=AssociationMany(ids=("region-1",)))
    assert offer.regions.ids == ("region-1",)
    print("Reciprocal pair: accepted")


def one_way_link() -> None:
    """Accept an intentionally unpaired association."""
    validate_entity_fields([BookmarkCoreEntity])
    validate_entity_inverses([BookmarkCoreEntity])
    bookmark = BookmarkCoreEntity(offer=AssociationOne(id="offer-1"))
    assert bookmark.offer.id == "offer-1"
    print("NoInverse link: accepted")


def old_pair_refusal() -> None:
    """Refuse the old one-sided inverse declaration."""
    try:
        validate_entity_inverses([OldRegionCoreEntity])
    except EntityFieldDeclarationError as error:
        assert error.field_name == "offer"
        assert (
            type(error).__name__ + ": " + str(error)
            == "EntityFieldDeclarationError: Field 'offer' on entity 'OldRegionCoreEntity' is invalid: the reverse field 'regions' on OldOfferCoreEntity declares no Inverse (it is NoInverse or missing a direction marker); declare a reciprocal Inverse(...) on both endpoints."
        )
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("A one-sided inverse was accepted")


def main() -> None:
    """Run the related direction cases."""
    reciprocal_pair()
    one_way_link()
    old_pair_refusal()


if __name__ == "__main__":
    main()
