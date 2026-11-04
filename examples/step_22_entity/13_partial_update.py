"""Load one more field of a partial entity.

The order identifier was loaded first and the total later. A copy with the
total holds it as loaded; the currency, still not loaded, still cannot be read.
A partial entity given every field is the same as the full one.

Run: uv run python examples/step_22_entity/13_partial_update.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, FieldNotLoadedError
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Describe an order with a total and a currency."""

    id: str = Field(description="Order identifier")
    total: float = Field(ge=0, description="Order total")
    currency: str = Field(default="RUB", description="Currency code")


order = OrderCoreEntity.partial(id="ord-5")
updated = order.model_copy(update={"total": 42.0})
print("total loaded:", updated.is_field_loaded("total"), updated.total)
print("currency loaded:", updated.is_field_loaded("currency"))
try:
    print(updated.currency)
except FieldNotLoadedError as exc:
    print("reading currency:", type(exc).__name__)
else:
    raise AssertionError("An unloaded currency must not be readable")

every = OrderCoreEntity.partial(id="ord-5", total=42.0, currency="EUR")
full = OrderCoreEntity(id="ord-5", total=42.0, currency="EUR")
print("partial with every field == full:", every == full)
print("partial with the id only == full:", order == full)
