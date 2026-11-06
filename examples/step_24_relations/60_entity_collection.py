"""A collection of structural entities needs a relation container.
Run: .venv/bin/python examples/step_24_relations/60_entity_collection.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""

    name = "example"
    description = "Explicit entity fields"


@meta(description="Where ExampleStorage keeps its rows")
class ExampleDataSource(InMemoryDataSource):
    """The store ExampleStorage works with."""


@meta(description="Stores the example entities", domain=ExampleDomain)
class ExampleStorage(BaseStorage[ExampleDataSource]):
    """Hold the example entities."""


@entity(description="Related object", resource=ExampleStorage)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""

    id: str = Field(description="Identifier")


@entity(description="Host object", resource=ExampleStorage)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""

    target: list[TargetCoreEntity] = Field(description="Targets")


def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError

    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert (
            type(error).__name__ + ": " + str(error)
            == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: the field's type is a collection of an entity (list[__main__.TargetCoreEntity]); a collection is not a relation. Declare the many relationship (Annotated[AssociationMany[TargetCoreEntity], Inverse(...) or NoInverse()] = Field(description=...))."
        )
    else:
        raise AssertionError("The invalid declaration was accepted")


if __name__ == "__main__":
    main()
