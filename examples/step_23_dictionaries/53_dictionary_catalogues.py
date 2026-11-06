"""Validate dictionary declarations and their supported boundaries.
Run: .venv/bin/python examples/step_23_dictionaries/53_dictionary_catalogues.py


"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class Shop53Domain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Where Shop53Storage keeps its rows")
class Shop53DataSource(InMemoryDataSource):
    """The store Shop53Storage works with."""


@meta(description="Stores the shop53 entities", domain=Shop53Domain)
class Shop53Storage(BaseStorage[Shop53DataSource]):
    """Hold the shop53 entities."""


class EmptyEnumEntity(BaseEnumEntity):
    """Declare no values; ``@entity`` refuses an empty dictionary, so this one stays undecorated."""


@entity(description="Offer", resource=Shop53Storage)
class Offer53CoreEntity(BaseCoreEntity):
    """Type a field with a dictionary that declares nothing."""

    id: str = Field(description="Offer identifier")
    region: Annotated[AssociationOne[EmptyEnumEntity], NoInverse()] = Field(description="Primary region")


def case_53() -> None:
    """Run this one learning experiment."""
    try:
        validate_entity_fields([Offer53CoreEntity])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ":", error)
    else:
        raise AssertionError("Expected declaration refusal")


class Shop54Domain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Where Shop54Storage keeps its rows")
class Shop54DataSource(InMemoryDataSource):
    """The store Shop54Storage works with."""


@meta(description="Stores the shop54 entities", domain=Shop54Domain)
class Shop54Storage(BaseStorage[Shop54DataSource]):
    """Hold the shop54 entities."""


@exclude_graph_model
@entity(description="Regions kept out of the graph", resource=Shop54Storage)
class HiddenRegion54EnumEntity(BaseEnumEntity):
    """Stay out of the graph on purpose."""

    EU = value(code="eu", display_name="Europe")


@entity(description="Offer", resource=Shop54Storage)
class Offer54CoreEntity(BaseCoreEntity):
    """Reference a dictionary the graph does not carry."""

    id: str = Field(description="Offer identifier")
    region: Annotated[AssociationOne[HiddenRegion54EnumEntity], NoInverse()] = Field(description="Primary region")


def case_54() -> None:
    """Run this one learning experiment."""
    try:
        validate_entity_fields([Offer54CoreEntity])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ":", error)
    else:
        raise AssertionError("Expected declaration refusal")


def main() -> None:
    """Run the related declaration cases."""
    case_53()
    case_54()


if __name__ == "__main__":
    main()
