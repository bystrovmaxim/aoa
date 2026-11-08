"""Share a lifecycle across databases.

A state type declares no resource of its own: it is stored with the entities whose
``Lifecycle[...]`` uses it. A lifecycle is a fact of the model, like a relation, so entities of
two databases may share one state type, and each carries its own lifecycle.

Run: uv run python examples/step_25_lifecycle/23_lifecycle_across_resources.py
"""

import json

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseStateEntity, Lifecycle, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseStorage


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


class SupportDomain(BaseDomain):
    """Group the support desk declarations."""

    name = "support"
    description = "Support"


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Paid")


class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Allow a draft to become paid."""

    _template = (
        Lifecycle()
        .state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial()
        .state(OrderStateEntity.PAID).final()
    )


@entity(description="Customer order", domain=StoreDomain)
class SalesOrderCoreEntity(BaseCoreEntity):
    """An order with a status."""

    id: str = Field(description="Order identifier")
    lifecycle: OrderLifecycle = Field(description="Order status")


@meta(description="Primary relational store")
@entities(
    SalesOrderCoreEntity,
)
class StorefrontDatabaseStorage(BaseStorage):
    """The orders, in the storefront database."""

    @classmethod
    def get_wrapper_class(cls):
        """No wrapper: this example never opens the resource."""
        return None


@entity(description="Return", domain=SupportDomain)
class ReturnCoreEntity(BaseCoreEntity):
    """A return in the other database that reuses the order's statuses."""

    id: str = Field(description="Return identifier")
    lifecycle: OrderLifecycle = Field(description="Return status")


@meta(description="Support desk store")
@entities(
    ReturnCoreEntity,
)
class SupportDatabaseStorage(BaseStorage):
    """The returns, in the support desk database."""

    @classmethod
    def get_wrapper_class(cls):
        """No wrapper: this example never opens the resource."""
        return None


# Run the case.
graph = json.loads(create_node_graph_coordinator().to_json())
short = {node["id"]: node["label"] for node in graph["nodes"]}
for edge in graph["edges"]:
    if edge["type"] == "domain" and short[edge["source_id"]] in ("SalesOrderCoreEntity", "ReturnCoreEntity"):
        states = sorted(node["label"] for node in graph["nodes"] if node["type"].startswith("State") and node["id"].startswith(edge["source_id"] + ":"))
        print(short[edge["source_id"]], "in", short[edge["target_id"]] + ":", ", ".join(states))
