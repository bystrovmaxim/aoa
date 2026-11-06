"""Validate dictionary declarations and their supported boundaries.
Run: .venv/bin/python examples/step_23_dictionaries/55_refusal_diagnostics.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseSpecEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class Shop55Domain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Where Shop55Storage keeps its rows")
class Shop55DataSource(InMemoryDataSource):
    """The store Shop55Storage works with."""


@meta(description="Stores the shop55 entities", domain=Shop55Domain)
class Shop55Storage(BaseStorage[Shop55DataSource]):
    """Hold the shop55 entities."""


@entity(description="First entity", resource=Shop55Storage)
class FirstCoreEntity(BaseCoreEntity):
    """Be the first member of each shape."""

    id: str = Field(description="Identifier")


@entity(description="Second entity", resource=Shop55Storage)
class SecondSpecEntity(BaseSpecEntity):
    """Be the second member of each shape."""

    id: str = Field(description="Identifier")


@entity(description="Union host", resource=Shop55Storage)
class UnionCoreEntity(BaseCoreEntity):
    """Name two entities on one field."""

    ref: FirstCoreEntity | SecondSpecEntity = Field(description="Union")


@entity(description="Mixed collection host", resource=Shop55Storage)
class MixedCoreEntity(BaseCoreEntity):
    """Collect two different entities in one field."""

    ref: tuple[FirstCoreEntity, SecondSpecEntity] = Field(description="Mixed collection")


@entity(description="Mapping host", resource=Shop55Storage)
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
