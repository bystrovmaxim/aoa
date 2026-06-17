"""
01_graph.py — The graph Maxitor renders is built from your code

Maxitor doesn't read YAML or Confluence — it renders the node graph the machine
assembles from the intents you already declared: domains, Actions, aspects,
@depends resources, @check_roles roles, entities, relations, lifecycles. Code
changes -> the graph changes.

This script declares a small domain and then introspects the SAME graph Maxitor
serves (machine.graph_coordinator). No browser needed: it prints the node-type
and edge-type breakdown the four Maxitor views are drawn from.

Maxitor itself is an AOA app: its backend is Actions exposed via FastApiAdapter,
serving this graph as JSON (GET /api/v1/full-graph, .../list-entities, etc.).

Tutorial: ../../docs/tutorials/step-26-maxitor_draft.md  ·  topic: Maxitor (system graph)

Run:
    uv run python examples/step_26_maxitor/01_graph.py
"""

from __future__ import annotations

from collections import Counter
from typing import Annotated

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseEntity,
    Inverse,
    Lifecycle,
    Rel,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


class ManagerRole(ApplicationRole):
    name = "manager"
    description = "Store manager"


@meta(description="Pricing service", domain=ShopDomain)
class PricingService(BaseResource):
    def price(self, sku: str) -> float:
        return {"sku-1": 8990.0}.get(sku, 0.0)

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None


class OrderLifecycle(Lifecycle):
    _template = (
        Lifecycle()
        .state("new", "New").to("paid", "cancelled").initial()
        .state("paid", "Paid").to("shipped").intermediate()
        .state("shipped", "Shipped").final()
        .state("cancelled", "Cancelled").final()
    )


@entity(description="Customer", domain=ShopDomain)
class CustomerEntity(BaseEntity):
    id: str = Field(description="Customer id")
    name: str = Field(description="Display name")
    orders: Annotated[
        AssociationMany[OrderEntity],
        Inverse(OrderEntity, "customer"),
    ] = Rel(description="Orders of this customer")


@entity(description="Order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    total: float = Field(ge=0, description="Order total")
    lifecycle: OrderLifecycle = Field(description="Order lifecycle")
    customer: Annotated[
        AssociationOne[CustomerEntity],
        Inverse(CustomerEntity, "orders"),
    ] = Rel(description="Customer who placed the order")


CustomerEntity.model_rebuild()
OrderEntity.model_rebuild()


class PlaceOrderParams(BaseParams):
    sku: str = Field(description="SKU")


class PlaceOrderResult(BaseResult):
    total: float = Field(description="Order total")


@meta(description="Place an order", domain=ShopDomain)
@check_roles(ManagerRole)
@depends(PricingService)
class PlaceOrderAction(BaseAction[PlaceOrderParams, PlaceOrderResult]):

    @regular_aspect("Price the order")
    @result_float("total", required=True, min_value=0)
    async def price_aspect(self, params, state, box, connections):
        return {"total": (await box.resolve(PricingService)).price(params.sku)}

    @summary_aspect("Confirm")
    async def confirm_summary(self, params, state, box, connections):
        return PlaceOrderResult(total=state["total"])


def main() -> None:
    # Building the machine builds the graph — the same one Maxitor renders.
    machine = ActionProductMachine()
    nodes = list(machine.graph_coordinator.get_all_nodes())
    edges = [e for n in nodes for e in n.get_all_edges()]

    print(f"Graph assembled from code: {len(nodes)} nodes, {len(edges)} edges\n")

    print("Node types (what the Full-graph view shows):")
    for node_type, count in sorted(Counter(n.node_type for n in nodes).items()):
        print(f"  {node_type:<16} {count}")

    print("\nEdge types (relations Maxitor draws between them):")
    for edge_name, count in sorted(Counter(e.edge_name for e in edges).items()):
        print(f"  {edge_name:<16} {count}")

    print("\nNo diagram was drawn by hand — this is the running system's own graph.")


if __name__ == "__main__":
    main()
