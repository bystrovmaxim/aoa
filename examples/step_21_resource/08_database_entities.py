"""A resource is a database, and it lists the entities that lie in it.

``@entities`` on a resource names the entities of its database. The resource's ``@meta`` takes
no domain: one database keeps entities of several domains, and each entity names its own. The
graph links the resource to every entity it lists.

Run: uv run python examples/step_21_resource/08_database_entities.py
"""

import json

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseStorage


class StoreDomain(BaseDomain):
    """Group the shop's orders."""

    name = "store"
    description = "Store"


class SupportDomain(BaseDomain):
    """Group the support desk."""

    name = "support"
    description = "Support"


@entity(description="Customer order", domain=StoreDomain)
class OrderCoreEntity(BaseCoreEntity):
    """An order of the store."""

    id: str = Field(description="Order identifier")


@entity(description="Support ticket", domain=SupportDomain)
class TicketCoreEntity(BaseCoreEntity):
    """A ticket of the support desk."""

    id: str = Field(description="Ticket identifier")


@meta(description="The shop database")
@entities(OrderCoreEntity, TicketCoreEntity)
class ShopDatabaseStorage(BaseStorage):
    """One database: the store's orders and the support desk's tickets lie in it."""


# Run the case.
graph = json.loads(create_node_graph_coordinator().to_json())
print("schema_version:", graph["schema_version"])
shown = ("ShopDatabaseStorage", "OrderCoreEntity", "TicketCoreEntity")
for edge in sorted(graph["edges"], key=lambda edge: (edge["type"], edge["source_id"], edge["target_id"])):
    if edge["type"] in ("resource_entity", "domain") and edge["source_id"] in shown:
        print(f"{edge['type']}: {edge['source_id']} -> {edge['target_id']}")
