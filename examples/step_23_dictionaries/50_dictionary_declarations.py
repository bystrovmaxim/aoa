"""Validate dictionary declarations and their supported boundaries.
Run: .venv/bin/python examples/step_23_dictionaries/50_dictionary_declarations.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, NoRelation, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class Shop50Domain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Where Shop50Storage keeps its rows")
class Shop50DataSource(InMemoryDataSource):
    """The store Shop50Storage works with."""


@meta(description="Stores the shop50 entities", domain=Shop50Domain)
class Shop50Storage(BaseStorage[Shop50DataSource]):
    """Hold the shop50 entities."""


@entity(description="Regions the shop sells in", resource=Shop50Storage)
class Region50EnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""

    EU = value(code="eu", display_name="Europe")
    US = value(code="us", display_name="United States")


@entity(description="Offer", resource=Shop50Storage)
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


@meta(description="Where Shop51Storage keeps its rows")
class Shop51DataSource(InMemoryDataSource):
    """The store Shop51Storage works with."""


@meta(description="Stores the shop51 entities", domain=Shop51Domain)
class Shop51Storage(BaseStorage[Shop51DataSource]):
    """Hold the shop51 entities."""


@entity(description="Regions the shop sells in", resource=Shop51Storage)
class Region51EnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""

    EU = value(code="eu", display_name="Europe")


@entity(description="Offer", resource=Shop51Storage)
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


@meta(description="Where Shop52Storage keeps its rows")
class Shop52DataSource(InMemoryDataSource):
    """The store Shop52Storage works with."""


@meta(description="Stores the shop52 entities", domain=Shop52Domain)
class Shop52Storage(BaseStorage[Shop52DataSource]):
    """Hold the shop52 entities."""


@entity(description="Regions the shop sells in", resource=Shop52Storage)
class Region52EnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""

    EU = value(code="eu", display_name="Europe")


@entity(description="Offer", resource=Shop52Storage)
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
