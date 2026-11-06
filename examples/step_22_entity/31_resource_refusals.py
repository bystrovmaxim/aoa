"""Name exactly one concrete resource.

``resource=`` takes one class that is a resource, is not one of the kind bases the graph leaves
out, and declares its domain with ``@meta``. Everything else is refused when the class is
defined, naming the entity and what it was given.

Run: uv run python examples/step_22_entity/31_resource_refusals.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, EntityDecoratorError
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource
from aoa.action_machine.resources.base_storage import BaseStorage


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


@meta(description="Where StorefrontDatabaseStorage keeps its rows")
class StorefrontDataSource(InMemoryDataSource):
    """The store StorefrontDatabaseStorage works with."""


@meta(description="Primary relational store", domain=StoreDomain)
class StorefrontDatabaseStorage(BaseStorage[StorefrontDataSource]):
    """The shop's database."""


@meta(description="Session cache", domain=StoreDomain)
class StorefrontSessionCacheStorage(BaseStorage):
    """The shop's session cache."""


class UndeclaredDatabaseStorage(BaseStorage):
    """A storage that never says which domain it serves."""


def declare(resource: object) -> None:
    """Declare one order stored by ``resource`` and print the refusal."""
    try:

        @entity(description="Customer order", resource=resource)  # type: ignore[arg-type]
        class SalesOrderCoreEntity(BaseCoreEntity):
            """A customer's order."""

            id: str = Field(description="Order identifier")

    except EntityDecoratorError as error:
        print(type(error).__name__ + ":", error)
    else:
        raise AssertionError(f"resource={resource!r} was accepted")


# Run the case.
declare(StoreDomain)
declare(BaseStorage)
declare(UndeclaredDatabaseStorage)
declare((StorefrontDatabaseStorage, StorefrontSessionCacheStorage))
