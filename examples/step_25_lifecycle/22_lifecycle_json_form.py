"""Send an entity with a lifecycle as JSON and read it back.

A lifecycle field goes out as its current status's reference: the code, the
label and the status's own fields under properties. It comes back from
{"code": ...}, which selects the declared status of the template, so the status
read back is the catalogue's object.

Run: uv run python examples/step_25_lifecycle/22_lifecycle_json_form.py
"""

from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseCoreEntity, BaseStateEntity, Lifecycle, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Where ShopStorage keeps its rows")
class ShopDataSource(InMemoryDataSource):
    """The store ShopStorage works with."""


@meta(description="Stores the shop entities", domain=ShopDomain)
class ShopStorage(BaseStorage[ShopDataSource]):
    """Hold the shop entities."""


@entity(description="Order status", resource=ShopStorage)
class OrderStateEntity(BaseStateEntity):
    """Describe each status of an order."""

    receipt_required: bool = Field(default=False, description="A receipt is required")
    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Payment received", receipt_required=True)


class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """A draft order is paid."""

    _template = (
        Lifecycle().state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial()
        .state(OrderStateEntity.PAID).final()
    )


@entity(description="Customer order", resource=ShopStorage)
class OrderCoreEntity(BaseCoreEntity):
    """An order and its lifecycle."""

    id: str = Field(description="Order identifier")
    lifecycle: OrderLifecycle = Field(description="Order lifecycle")


print("1) JSON out")
order = OrderCoreEntity(id="ord-1", lifecycle=OrderLifecycle("paid"))
print("   JSON:", order.model_dump(mode="json")["lifecycle"])
print("   Python dump keeps:", type(order.model_dump()["lifecycle"]).__name__)

print("2) JSON in")
back = OrderCoreEntity.model_validate({"id": "ord-1", "lifecycle": {"code": "paid"}})
print("   current state:", back.lifecycle.current_state)
print("   the declared status:", back.lifecycle.current_status is OrderStateEntity.PAID)
print("   equal to what went out:", OrderCoreEntity.model_validate_json(order.model_dump_json()) == order)

print("3) An unknown code")
try:
    OrderCoreEntity.model_validate({"id": "ord-2", "lifecycle": {"code": "shipped"}})
except ValidationError as exc:
    print("   ValidationError:", exc.errors()[0]["msg"])
else:
    raise AssertionError("shipped is not a state of the template")

schema = OrderCoreEntity.model_json_schema(mode="validation")["properties"]["lifecycle"]
print("4) Schema codes:", schema["properties"]["code"]["enum"])
