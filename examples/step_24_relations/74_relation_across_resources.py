"""Relate entities of two databases.

A relation is a fact of the model: it says the two entities are related and promises no
foreign key, no join and no shared transaction. So it may join entities of any resources,
even resources of two databases, and the model accepts it.

Run: uv run python examples/step_24_relations/74_relation_across_resources.py
"""

import json
from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
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


@entity(description="Customer order", domain=StoreDomain)
class SalesOrderCoreEntity(BaseCoreEntity):
    """A customer's order."""

    id: str = Field(description="Order identifier")


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


@entity(description="Support ticket", domain=SupportDomain)
class SupportTicketCoreEntity(BaseCoreEntity):
    """A ticket about an order of the other database."""

    id: str = Field(description="Ticket identifier")
    order: Annotated[AssociationOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")


@meta(description="Support desk store")
@entities(
    SupportTicketCoreEntity,
)
class SupportDatabaseStorage(BaseStorage):
    """The support tickets, in the support desk database."""

    @classmethod
    def get_wrapper_class(cls):
        """No wrapper: this example never opens the resource."""
        return None


SupportTicketCoreEntity.model_rebuild()

# Run the case.
graph = json.loads(create_node_graph_coordinator().to_json())
short = {node["id"]: node["label"] for node in graph["nodes"]}
for edge in graph["edges"]:
    if edge["type"] == "entity_relation":
        print(edge["type"] + ":", short[edge["source_id"]], "->", short[edge["target_id"]])
