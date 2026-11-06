"""A nullable relation may be omitted only with an explicit default.
Run: .venv/bin/python examples/step_24_relations/53_optional_relation.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
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
    target: Annotated[AssociationOne[TargetCoreEntity] | None, NoInverse()] = Field(default=None, description="Target")

def main() -> None:
    """Run the example and assert its result."""
    ActionProductMachine(loggers=[])
    item = HostCoreEntity()
    print("Omitted relation:", item.target)
    assert item.target is None

if __name__ == "__main__":
    main()
