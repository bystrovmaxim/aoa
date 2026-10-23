"""A nullable relation may be omitted only with an explicit default.
Run: .venv/bin/python examples/step_21_relations/53_optional_relation.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
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
