"""Store an entity in the resource that holds it.

An entity is a row kept somewhere. ``@entity`` names the resource that keeps it, and the entity
takes its domain from that resource's ``@meta``. The graph shows both: an ``entity_resource``
edge to the resource and a ``domain`` edge to the resource's domain.

Run: uv run python examples/step_22_entity/29_stored_by_resource.py
"""

import json

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


@meta(description="Where StorefrontDatabase keeps its rows")
class StorefrontDataSource(InMemoryDataSource):
    """The store StorefrontDatabase works with."""


@meta(description="Primary relational store", domain=StoreDomain)
class StorefrontDatabase(BaseStorage[StorefrontDataSource]):
    """The database the shop's orders live in."""


@entity(description="Customer order", resource=StorefrontDatabase)
class SalesOrderCoreEntity(BaseCoreEntity):
    """A customer's order, stored by the shop's database."""

    id: str = Field(description="Order identifier")


# Run the case.
print("resource:", EntityIntentResolver.resolve_resource_type(SalesOrderCoreEntity).__name__)
print("domain:", EntityIntentResolver.resolve_domain_type(SalesOrderCoreEntity).__name__)
graph = json.loads(create_node_graph_coordinator().to_json())
print("schema_version:", graph["schema_version"])
for edge in graph["edges"]:
    if edge["source_id"] == "SalesOrderCoreEntity" and edge["type"] in ("entity_resource", "domain"):
        print(f"{edge['type']}: {edge['source_id']} -> {edge['target_id']} ({edge['relationship']})")
