"""Name the domain an entity belongs to.

An entity is a domain object. ``@entity`` names its domain, and the graph shows one ``domain``
edge from the entity to it. The entity names no resource: the database that holds it lists it
with ``@entities``, and the graph links that database to it.

Run: uv run python examples/step_22_entity/29_entity_domain.py
"""

import json

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


@entity(description="Customer order", domain=StoreDomain)
class SalesOrderCoreEntity(BaseCoreEntity):
    """A customer's order."""

    id: str = Field(description="Order identifier")


@meta(description="Primary relational store")
@entities(
    SalesOrderCoreEntity,
)
class StorefrontDatabaseStorage(BaseStorage):
    """The database the shop's orders live in; the entity itself does not name it."""


# Run the case.
print("domain:", EntityIntentResolver.resolve_domain_type(SalesOrderCoreEntity).__name__)
graph = json.loads(create_node_graph_coordinator().to_json())
print("schema_version:", graph["schema_version"])
for edge in graph["edges"]:
    if "SalesOrderCoreEntity" in (edge["source_id"], edge["target_id"]) and edge["type"] in ("domain", "resource_entity"):
        print(f"{edge['type']}: {edge['source_id']} -> {edge['target_id']} ({edge['relationship']})")
