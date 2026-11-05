"""An entity cannot exist without a resource.

``@entity`` refuses a declaration that names no resource, and it has no ``domain`` parameter:
the domain comes from the resource, so there is one place to read it from.

Run: uv run python examples/step_22_entity/30_resource_required.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, EntityDecoratorError
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


# Run the case.
try:

    @entity(description="Customer order")
    class SalesOrderCoreEntity(BaseCoreEntity):
        """An order that names no resource."""

        id: str = Field(description="Order identifier")

except EntityDecoratorError as error:
    print(type(error).__name__ + ":", error)
else:
    raise AssertionError("An entity without a resource was accepted")

try:
    entity(description="Customer order", domain=StoreDomain)  # type: ignore[call-arg]
except TypeError as error:
    print(type(error).__name__ + ":", error)
else:
    raise AssertionError("domain= was accepted")
