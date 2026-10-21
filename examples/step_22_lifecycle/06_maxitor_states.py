"""Read the state list produced by Maxitor.

Load the exported graph into Maxitor and request its lifecycle diagram data.

Run: uv run python examples/step_22_lifecycle/06_maxitor_states.py
"""

from pydantic import Field
from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Carry presentation fields and a separate domain field."""

    sort_order: int = Field(description="Order within the state list")
    color: str = Field(default="#1565c0", description="State outline colour")
    fill_color: str = Field(default="#e3f2fd", description="State fill colour")
    requires_receipt: bool = Field(default=False, description="Whether a receipt is needed")


class OrderLifecycle(Lifecycle, StateVocabulary):
    """Keep the initial state first despite its high sort order."""

    DRAFT = OrderStateEntity(code="draft", display_name="Draft", sort_order=99)
    PAID = OrderStateEntity(code="paid", display_name="Payment received", sort_order=1, requires_receipt=True)
    CANCELLED = OrderStateEntity(code="cancelled", display_name="Cancelled", sort_order=2)
    _template = Lifecycle().state(DRAFT).to(PAID, CANCELLED).initial().state(PAID).final().state(CANCELLED).final()
import json
from aoa.action_machine.domain import BaseEntity, BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    """Group the entities in this example."""

    name = "shop"
    description = "Small shop"


@entity(description="Customer order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    """Attach the lifecycle to a model entity."""

    id: str = Field(description="Order identifier")
    lifecycle: OrderLifecycle = Field(description="Current order state")

import asyncio
from aoa.action_machine.context import Context
from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action import GetLifecycleFiniteAutomatonAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY, DuckDBGraphResource

# Run the case.
async def read_states():
    """Request the real Maxitor action without starting an HTTP server."""
    machine = ActionProductMachine(loggers=[])
    graph = json.loads(machine.graph_coordinator.to_json())
    lifecycle = next(node for node in graph["nodes"] if node["type"] == "Lifecycle")
    resource = DuckDBGraphResource.build_from_json(graph)
    result = await machine.run(
        Context(), GetLifecycleFiniteAutomatonAction(),
        GetLifecycleFiniteAutomatonAction.Params(lifecycle_graph_node_id=lifecycle["id"]),
        {DUCKDB_GRAPH_CONNECTION_KEY: resource},
    )
    states = result.lifecycle_finite_automaton["states"]
    assert [state["key"] for state in states] == ["draft", "paid", "cancelled"]
    paid = next(state for state in states if state["key"] == "paid")
    assert "requires_receipt" not in paid["attributes"]
    assert paid["attributes"]["color"] == "#1565c0"
    print("state order:", [state["key"] for state in states])
    print("paid label:", paid["display_name"])
    print("diagram attributes:", paid["attributes"])

asyncio.run(read_states())
