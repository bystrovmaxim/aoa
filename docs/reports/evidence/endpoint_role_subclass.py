"""Reproduce a custom ownership container bypassing compatibility validation.
Run: .venv/bin/python docs/reports/evidence/endpoint_role_subclass.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, CompositeMany, CompositeOne, Inverse
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class CustomCompositeOne[T](CompositeOne[T]):
    """Retain composition meaning through an ordinary container subclass."""


class SubclassDomain(BaseDomain):
    """Group the incompatible pair."""

    name = "container-subclass"
    description = "Container subclass reproduction"


@meta(description="Stores the subclass entities", domain=SubclassDomain)
class SubclassStorage(BaseStorage):
    """Hold the subclass entities."""


@entity(description="First owner", resource=SubclassStorage)
class FirstCoreEntity(BaseCoreEntity):
    """Declare an ownership endpoint through a subclass."""

    second: Annotated[CustomCompositeOne[SecondCoreEntity], Inverse(field_name="first")] = Field(description="Second")


@entity(description="Second owner", resource=SubclassStorage)
class SecondCoreEntity(BaseCoreEntity):
    """Declare the incompatible ownership reverse."""

    first: Annotated[CompositeMany[FirstCoreEntity], Inverse(field_name="second")] = Field(description="First")


def main() -> None:
    """Build the public machine with the incompatible pair."""
    FirstCoreEntity.model_rebuild()
    SecondCoreEntity.model_rebuild()
    machine = ActionProductMachine(loggers=[])
    assert machine.graph_coordinator.get_all_nodes()
    print("Custom composition / composition: machine built (validation gap)")


if __name__ == "__main__":
    main()
