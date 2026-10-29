"""
06_entity_kinds.py — the entity kinds of a graph, named by the graph, from any producer

Maxitor holds no list of kinds and no table of their names. ``GET /api/v1/list-entity-kinds``
answers the words the loaded graph states, ordered by word, each named by the graph's
``entity_kind_label`` or — when the graph names none — by the word with its first letter
capitalised. The ERD's Kinds filter is built from this answer.

The cases, with the real output at the bottom:

  1. an AOA graph: the kinds of its model, named by their kind bases;
  2. a graph from another producer: kinds AOA does not ship, one of them named;
  3. a graph whose rows state no kind: it loads, and the rows are listed as ``unknown``;
  4. a row whose kind is not a string: the load is refused and names the row.

Output:

    1. An AOA graph
       {'entity_kind': 'core', 'label': 'Core'}
       {'entity_kind': 'enum', 'label': 'Enumeration'}

    2. Another producer's graph
       {'entity_kind': 'aggregate', 'label': 'Aggregate root'}
       {'entity_kind': 'event', 'label': 'Event'}
       {'entity_kind': 'link', 'label': 'Link'}

    3. A graph that states no kind
       {'entity_kind': 'unknown', 'label': 'Unknown'}

    4. A kind that is not a string
       GET /api/v1/list-entity-kinds -> 422 Entity node 'shop.BrokenEntity': properties.entity_kind must be a string, got int.

Run: uv run python examples/step_26_maxitor/06_entity_kinds.py
"""

import json
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from maxitor.front.api.app import create_app
from maxitor.front.api.graph_store import GraphEntry, GraphStore
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_SOURCE = "https://shop.example/graph-json"
_EMPTY_SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Currency", domain=ShopDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary of currencies."""

    EUR = value(code="eur", display_name="Euro")


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Describe an order independently of its storage."""

    id: str = Field(description="Order identifier")


def _list_kinds(graph: dict[str, Any]) -> Any:
    """Serve ``graph`` for one source and read ``list-entity-kinds`` the way the client does."""

    async def builder(source: str) -> GraphEntry:
        """Build the one graph this example serves."""
        return GraphEntry(source=source, graph=DuckDBGraphResource.build_from_json(graph), sidebar=_EMPTY_SIDEBAR, last_read=0.0)

    app = create_app()
    app.state.graph_store = GraphStore(builder)
    return TestClient(app, raise_server_exceptions=False).get("/api/v1/list-entity-kinds", params={"source": _SOURCE})


def _entity(identifier: str, **properties: Any) -> dict[str, Any]:
    """An ``Entity`` node as any producer may send it."""
    return {"id": identifier, "type": "Entity", "label": identifier.rsplit(".", 1)[-1], "properties": {"description": "", **properties}}


def _graph(*nodes: dict[str, Any]) -> dict[str, Any]:
    """A graph document holding only ``nodes``."""
    return {"schema_version": "1.0", "nodes": list(nodes), "edges": []}


print("1. An AOA graph")
aoa_graph = json.loads(ActionProductMachine(loggers=[]).graph_coordinator.to_json())
for row in _list_kinds(aoa_graph).json()["list_entity_kinds"]:
    print("  ", row)

print("\n2. Another producer's graph")
foreign = _graph(
    _entity("shop.OrderEntity", entity_kind="aggregate", entity_kind_label="Aggregate root"),
    _entity("shop.PlacedEntity", entity_kind="event"),
    _entity("shop.LinkEntity", entity_kind="link"),
)
for row in _list_kinds(foreign).json()["list_entity_kinds"]:
    print("  ", row)

print("\n3. A graph that states no kind")
for row in _list_kinds(_graph(_entity("shop.LegacyEntity"))).json()["list_entity_kinds"]:
    print("  ", row)

print("\n4. A kind that is not a string")
response = _list_kinds(_graph(_entity("shop.BrokenEntity", entity_kind=5)))
print("   GET /api/v1/list-entity-kinds ->", response.status_code, response.json()["detail"])
