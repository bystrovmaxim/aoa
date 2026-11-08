"""Relate entities of two domains that lie in one database.

A resource is a database, so two domains whose data lie in one database share one resource,
and it lists the entities of both. A relation between those entities is part of the model like
any other, and the graph links the database to each entity it lists.

Run: uv run python examples/step_24_relations/75_relation_inside_one_database.py
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


@entity(description="Support ticket", domain=SupportDomain)
class SupportTicketCoreEntity(BaseCoreEntity):
    """A ticket about an order; the ticket and the order lie in the same database."""

    id: str = Field(description="Ticket identifier")
    order: Annotated[AssociationOne[SalesOrderCoreEntity], NoInverse()] = Field(description="Order")


@meta(description="The shop database")
@entities(
    SalesOrderCoreEntity,
    SupportTicketCoreEntity,
)
class ShopDatabaseStorage(BaseStorage):
    """One database keeps the store's orders and the support desk's tickets."""


SupportTicketCoreEntity.model_rebuild()

# Run the case.
graph = json.loads(create_node_graph_coordinator().to_json())
short = {node["id"]: node["label"] for node in graph["nodes"]}
for edge in graph["edges"]:
    if edge["type"] in ("entity_relation", "resource_entity"):
        print(edge["type"] + ":", short[edge["source_id"]], "->", short[edge["target_id"]])
