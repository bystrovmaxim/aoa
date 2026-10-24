"""Validate dictionary declarations and their supported boundaries.
Run: .venv/bin/python examples/step_20_dictionaries/50_dictionary_declarations.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, NoRelation, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity


class Shop50Domain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Regions the shop sells in", domain=Shop50Domain)
class Region50EnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""

    EU = value(code="eu", display_name="Europe")
    US = value(code="us", display_name="United States")


@entity(description="Offer", domain=Shop50Domain)
class Offer50CoreEntity(BaseCoreEntity):
    """Try to serve several regions from one field."""

    id: str = Field(description="Offer identifier")
    regions: tuple[Region50EnumEntity, ...] = Field(description="Regions served")


def case_50() -> None:
    """Run this one learning experiment."""
    try:
        validate_entity_fields([Offer50CoreEntity])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ":", error)
    else:
        raise AssertionError("Expected declaration refusal")


class Shop51Domain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Regions the shop sells in", domain=Shop51Domain)
class Region51EnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""

    EU = value(code="eu", display_name="Europe")


@entity(description="Offer", domain=Shop51Domain)
class Offer51CoreEntity(BaseCoreEntity):
    """Wrap a shared value in an association."""

    id: str = Field(description="Offer identifier")
    region: Annotated[AssociationOne[Region51EnumEntity], NoInverse()] = Field(description="Primary region")


def case_51() -> None:
    """Run this one learning experiment."""
    validate_entity_fields([Offer51CoreEntity])
    offer = Offer51CoreEntity(id="offer-1", region=AssociationOne(id="eu"))
    assert offer.region.entity is Region51EnumEntity.EU
    print("Complete dictionary association:", offer.region.code)


class Shop52Domain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Regions the shop sells in", domain=Shop52Domain)
class Region52EnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""

    EU = value(code="eu", display_name="Europe")


@entity(description="Offer", domain=Shop52Domain)
class Offer52CoreEntity(BaseCoreEntity):
    """Mark a reference as an embedded value."""

    id: str = Field(description="Offer identifier")
    region: Annotated[Region52EnumEntity, NoRelation("a value")] = Field(description="Primary region")


def case_52() -> None:
    """Run this one learning experiment."""
    try:
        validate_entity_fields([Offer52CoreEntity])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ":", error)
    else:
        raise AssertionError("Expected declaration refusal")


def main() -> None:
    """Run the related declaration cases."""
    case_50()
    case_51()
    case_52()


if __name__ == "__main__":
    main()
