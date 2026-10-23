"""Validate dictionary declarations and their supported boundaries.
Run: .venv/bin/python examples/step_20_dictionaries/55_refusal_diagnostics.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseSpecEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity


class Shop55Domain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="First entity", domain=Shop55Domain)
class FirstCoreEntity(BaseCoreEntity):
    """Be the first member of each shape."""

    id: str = Field(description="Identifier")


@entity(description="Second entity", domain=Shop55Domain)
class SecondSpecEntity(BaseSpecEntity):
    """Be the second member of each shape."""

    id: str = Field(description="Identifier")


@entity(description="Union host", domain=Shop55Domain)
class UnionCoreEntity(BaseCoreEntity):
    """Name two entities on one field."""

    ref: FirstCoreEntity | SecondSpecEntity = Field(description="Union")


@entity(description="Mixed collection host", domain=Shop55Domain)
class MixedCoreEntity(BaseCoreEntity):
    """Collect two different entities in one field."""

    ref: tuple[FirstCoreEntity, SecondSpecEntity] = Field(description="Mixed collection")


@entity(description="Mapping host", domain=Shop55Domain)
class MappingCoreEntity(BaseCoreEntity):
    """Map a key to an entity."""

    ref: dict[str, FirstCoreEntity] = Field(description="Mapping")


def case_55() -> None:
    """Run this one learning experiment."""
    for entity_cls in (UnionCoreEntity, MixedCoreEntity, MappingCoreEntity):
        try:
            validate_entity_fields([entity_cls])
        except EntityFieldDeclarationError as error:
            print(type(error).__name__ + ":", error)
        else:
            raise AssertionError("Expected declaration refusal")


def main() -> None:
    """Run the related declaration cases."""
    case_55()


if __name__ == "__main__":
    main()
