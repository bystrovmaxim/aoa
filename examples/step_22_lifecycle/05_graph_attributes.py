"""Export a state description to the graph.

Build the actual model graph and inspect the paid state row.

Run: uv run python examples/step_22_lifecycle/05_graph_attributes.py
"""

import json

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseStateEntity, Lifecycle, value
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

    requires_receipt: bool = Field(default=False, description="Whether a receipt is needed")

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Payment received", requires_receipt=True)


class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Collect statuses and declare their allowed transition."""

    _template = (
        Lifecycle()
        .state(OrderStateEntity.DRAFT)
        .to(OrderStateEntity.PAID)
        .initial()
        .state(OrderStateEntity.PAID)
        .final()
    )


class ShopDomain(BaseDomain):
    """Group the entities in this example."""

    name = "shop"
    description = "Small shop"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Attach the lifecycle to a model entity."""

    id: str = Field(description="Order identifier")
    lifecycle: OrderLifecycle = Field(description="Current order state")


# Run the case.
machine = ActionProductMachine(loggers=[])
graph = json.loads(machine.graph_coordinator.to_json())
row = next(
    node for node in graph["nodes"] if node["type"].startswith("State") and node["properties"]["state_key"] == "paid"
)
assert row["id"].endswith(":lifecycle:lifecycle:paid")
assert row["label"] == "Payment received"
assert row["properties"]["attributes"]["requires_receipt"] is True
entities = [node for node in graph["nodes"] if node["type"] == "Entity"]
assert len(entities) == 1
print("key:", row["properties"]["state_key"])
print("label:", row["label"])
print("attributes:", row["properties"]["attributes"])
print("model entities:", len(entities))
