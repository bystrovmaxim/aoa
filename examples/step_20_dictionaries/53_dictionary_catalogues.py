"""Validate dictionary declarations and their supported boundaries.
Run: .venv/bin/python examples/step_20_dictionaries/53_dictionary_catalogues.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity


class Shop53Domain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


class EmptyEnumEntity(BaseEnumEntity):
    """Declare no values; ``@entity`` refuses an empty dictionary, so this one stays undecorated."""


@entity(description="Offer", domain=Shop53Domain)
class Offer53CoreEntity(BaseCoreEntity):
    """Type a field with a dictionary that declares nothing."""

    id: str = Field(description="Offer identifier")
    region: EmptyEnumEntity = Field(description="Primary region")


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


@exclude_graph_model
@entity(description="Regions kept out of the graph", domain=Shop54Domain)
class HiddenRegion54EnumEntity(BaseEnumEntity):
    """Stay out of the graph on purpose."""

    EU = value(code="eu", display_name="Europe")


@entity(description="Offer", domain=Shop54Domain)
class Offer54CoreEntity(BaseCoreEntity):
    """Reference a dictionary the graph does not carry."""

    id: str = Field(description="Offer identifier")
    region: HiddenRegion54EnumEntity = Field(description="Primary region")


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
