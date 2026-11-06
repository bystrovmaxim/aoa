"""Relate entities of two resources that share one database.

A resource is often a part of a database. When two resources name one data source, the
database they share, a relation between their entities is an ordinary join, and the model
accepts it. A resource that names no data source keeps its relations to itself.

Run: uv run python examples/step_24_relations/75_relation_inside_one_data_source.py
"""

import json
from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseDataSource, BaseStorage


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


@meta(description="Main shop database")
class ShopDataSource(BaseDataSource):
    """The one database the orders and the support tickets live in."""


@meta(description="Orders", domain=StoreDomain)
class OrdersStorage(BaseStorage[ShopDataSource]):
    """The part of the shop database that keeps orders."""

    def get_wrapper_class(self):
        """No wrapper: this example never opens the resource."""
        return None


@meta(description="Support desk", domain=StoreDomain)
class SupportStorage(BaseStorage[ShopDataSource]):
    """The part of the shop database that keeps support tickets."""

    def get_wrapper_class(self):
        """No wrapper: this example never opens the resource."""
        return None


@entity(description="Customer order", resource=OrdersStorage)
class SalesOrderCoreEntity(BaseCoreEntity):
    """A customer's order."""

    id: str = Field(description="Order identifier")


@entity(description="Support ticket", resource=SupportStorage)
class SupportTicketCoreEntity(BaseCoreEntity):
    """A ticket about an order kept by another resource of the same database."""

    id: str = Field(description="Ticket identifier")
    order: Annotated[AssociationOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")


SupportTicketCoreEntity.model_rebuild()

# Run the case.
graph = json.loads(create_node_graph_coordinator().to_json())
short = {node["id"]: node["label"] for node in graph["nodes"]}
for edge in graph["edges"]:
    if edge["type"] in ("resource_data_source", "entity_relation"):
        print(edge["type"] + ":", short[edge["source_id"]], "->", short[edge["target_id"]])
