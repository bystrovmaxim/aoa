"""Add behaviour without adding another kind.

A plain Python mixin can add a method. It does not describe a second entity kind.

Run: uv run python examples/step_20_entity/10_mixin.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


class LabelMixin:
    """Supply a label independently of entity classification."""

    def label(self) -> str:
        """Return a readable type label."""
        return type(self).__name__


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(LabelMixin, BaseCoreEntity):
    """Combine ordinary behaviour with one entity kind."""

    id: str = Field(description="Order identifier")

order = OrderCoreEntity(id="ord-1")
assert order.label() == "OrderCoreEntity"
print(order.label())
