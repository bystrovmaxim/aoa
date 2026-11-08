"""An entity cannot exist without a domain.

``@entity`` refuses a declaration that names no domain, and it has no ``resource`` parameter:
the entity names the domain itself.

Run: uv run python examples/step_22_entity/30_domain_required.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, EntityDecoratorError
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


# Run the case: an omitted domain is refused by the decorator's signature.
try:

    @entity(description="Customer order")
    class SalesOrderCoreEntity(BaseCoreEntity):
        """An order that names no domain."""

        id: str = Field(description="Order identifier")

except TypeError as error:
    print(type(error).__name__ + ":", error)
else:
    raise AssertionError("An entity without a domain was accepted")

# An explicit ``None`` is refused by the domain check.
try:
    entity(description="Customer order", domain=None)  # type: ignore[arg-type]
except EntityDecoratorError as error:
    print(type(error).__name__ + ":", error)
else:
    raise AssertionError("domain=None was accepted")

# ``resource=`` is gone: the signature no longer takes it.
try:
    entity(description="Customer order", resource=StoreDomain)  # type: ignore[call-arg]
except TypeError as error:
    print(type(error).__name__ + ":", error)
else:
    raise AssertionError("resource= was accepted")
