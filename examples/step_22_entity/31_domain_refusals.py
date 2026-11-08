"""Name exactly one domain.

``domain=`` takes one class that is a ``BaseDomain`` subclass; a declaration without one is
refused when the class is defined, naming the entity. ``resource=`` is gone, and the decorator
refuses it.

Run: uv run python examples/step_22_entity/31_domain_refusals.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, EntityDecoratorError
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


def declare(domain: object) -> None:
    """Declare one order in ``domain`` and print the refusal."""
    try:

        @entity(description="Customer order", domain=domain)  # type: ignore[arg-type]
        class SalesOrderCoreEntity(BaseCoreEntity):
            """A customer's order."""

            id: str = Field(description="Order identifier")

    except EntityDecoratorError as error:
        print(type(error).__name__ + ":", error)
    else:
        raise AssertionError(f"domain={domain!r} was accepted, but must be refused")


# Run the case.
declare(None)

try:
    entity(description="Customer order", resource=StoreDomain)  # type: ignore[call-arg]
except TypeError as error:
    print(type(error).__name__ + ":", error)
else:
    raise AssertionError("resource= was accepted")
