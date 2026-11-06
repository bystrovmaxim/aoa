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
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseDataSource, BaseStorage


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


class SupportDomain(BaseDomain):
    """Group the support desk declarations."""

    name = "support"
    description = "Support"


@meta(description="Storefront database")
class StorefrontDataSource(BaseDataSource):
    """The database the orders live in."""


@meta(description="Support desk database")
class SupportDataSource(BaseDataSource):
    """Another database: the one the returns live in."""


@meta(description="Primary relational store", domain=StoreDomain)
class StorefrontDatabase(BaseStorage[StorefrontDataSource]):
    """The orders, in the storefront database."""

    def get_wrapper_class(self):
        """No wrapper: this example never opens the resource."""
        return None


@meta(description="Support desk store", domain=SupportDomain)
class SupportDatabase(BaseStorage[SupportDataSource]):
    """The returns, in the support desk database."""

    def get_wrapper_class(self):
        """No wrapper: this example never opens the resource."""
        return None


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


@entity(description="Customer order", resource=StorefrontDatabase)
class SalesOrderCoreEntity(BaseCoreEntity):
    """An order with a status."""

    id: str = Field(description="Order identifier")
    lifecycle: OrderLifecycle = Field(description="Order status")


@entity(description="Return", resource=SupportDatabase)
class ReturnCoreEntity(BaseCoreEntity):
    """A return in the other database that reuses the order's statuses."""

    id: str = Field(description="Return identifier")
    lifecycle: OrderLifecycle = Field(description="Return status")


# Run the case.
graph = json.loads(create_node_graph_coordinator().to_json())
short = {node["id"]: node["label"] for node in graph["nodes"]}
for edge in graph["edges"]:
    if edge["type"] == "entity_resource" and short[edge["source_id"]] in ("SalesOrderCoreEntity", "ReturnCoreEntity"):
        states = sorted(node["label"] for node in graph["nodes"] if node["type"].startswith("State") and node["id"].startswith(edge["source_id"] + ":"))
        print(short[edge["source_id"]], "in", short[edge["target_id"]] + ":", ", ".join(states))
