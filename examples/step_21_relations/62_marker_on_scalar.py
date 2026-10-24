"""An embedded entity marker cannot mark a scalar.
Run: .venv/bin/python examples/step_21_relations/62_marker_on_scalar.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, NoRelation
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

    target: Annotated[str, NoRelation("Snapshot")] = Field(description="Text")


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
            == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation marks an embedded value, which no longer exists; this field's type is str, not an entity. Declare the field as an ordinary scalar."
        )
    else:
        raise AssertionError("The invalid declaration was accepted")


if __name__ == "__main__":
    main()
