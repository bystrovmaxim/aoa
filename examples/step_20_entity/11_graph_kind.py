"""Preserve the kind in the graph and Maxitor store.

The model graph records the kind as data. A consumer can read it without parsing the concrete class name.

Run: uv run python examples/step_20_entity/11_graph_kind.py
"""

import json

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Describe an order independently of its storage."""

    id: str = Field(description="Order identifier")
    total: float = Field(ge=0, description="Order total")

machine = ActionProductMachine(loggers=[])
payload = json.loads(machine.graph_coordinator.to_json())
row = next(n for n in payload["nodes"] if n["type"] == "Entity" and n["label"] == "OrderCoreEntity")
assert row["properties"]["entity_kind"] == "core"
store = DuckDBGraphResource.build_from_json(payload)
kind = store.execute_fetch_dicts("SELECT entity_kind FROM entity WHERE label = ?", ["OrderCoreEntity"])[0]["entity_kind"]
assert kind == "core"
print("graph:", row["properties"]["entity_kind"])
print("Maxitor store:", kind)
