# tests/action_machine/graph/test_resource_entity_graph.py
"""
The graph at protocol 2.0: a resource reaches each entity it lists with ``resource_entity``.

A resource is a database. It lists what lies in it with ``@entities(*entity_classes)``, and
the graph carries one ``resource_entity`` aggregation edge from the resource to each listed
entity — gateways included, since a gateway that answers with catalog entities says so. A
resource has no ``domain`` edge; the entity keeps its own. An entity may lie in two
databases, so two resources may reach it.

The coordinator refuses a listed entry without its edge and an edge that ends elsewhere
than at an entity node. Each built graph is a fresh interpreter.
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

import jsonschema
import pytest
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.edge_identity import edge_id
from aoa.action_machine.graph.edges.resource_entity_graph_edge import ResourceEntityGraphEdge
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.nodes.resource_graph_node import ResourceGraphNode
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseStorage
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

from ...support.isolated_entity_models import run_isolated_model

# ── Hand-built fixtures: the node and the refusals ─────────────────────────────────────


class _GraphDomain(BaseDomain):
    """A domain of the hand-built entities."""

    name = "resource_entity_graph"
    description = "Graph"


@exclude_graph_model
@entity(description="Customer order", domain=_GraphDomain)
class _OrderCoreEntity(BaseCoreEntity):
    """A listed entity of the hand-built database."""

    id: str = Field(description="Order id")


@exclude_graph_model
@entity(description="Product", domain=_GraphDomain)
class _ProductCoreEntity(BaseCoreEntity):
    """The second listed entity of the hand-built database."""

    id: str = Field(description="Product id")


@exclude_graph_model
@meta(description="The hand-built shop database")
@entities(_OrderCoreEntity, _ProductCoreEntity)
class _ShopDatabaseStorage(BaseStorage):
    """A database that lists two entities; excluded from global inspectors so fixture nodes build the graph."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None


def test_the_resource_node_returns_one_edge_per_listed_entity() -> None:
    """``get_all_edges`` carries an edge per ``@entities`` entry, in declaration order."""
    node = ResourceGraphNode(_ShopDatabaseStorage)
    edges = node.get_all_edges()

    assert [edge.edge_name for edge in edges] == ["resource_entity", "resource_entity"]
    assert [edge.target_node_id for edge in edges] == [
        TypeIntrospection.full_qualname(_OrderCoreEntity),
        TypeIntrospection.full_qualname(_ProductCoreEntity),
    ]


def test_a_resource_entity_edge_is_an_aggregation_dag_link() -> None:
    """The row is Aggregation, ``is_dag`` true, empty properties, and the default id."""
    edge = ResourceEntityGraphEdge(_OrderCoreEntity)
    row = edge.to_dict(source_id="shop.ShopDatabaseStorage")

    assert row == {
        "source_id": "shop.ShopDatabaseStorage",
        "target_id": TypeIntrospection.full_qualname(_OrderCoreEntity),
        "type": "resource_entity",
        "relationship": "Aggregation",
        "is_dag": True,
        "properties": {},
    }
    assert edge_id(row) == f"shop.ShopDatabaseStorage|resource_entity|{row['target_id']}"


class _Axis:
    """Root type of the harness inspector."""


class _FixedGraphNode(BaseGraphNode[object]):
    """A node with a given type, host object and edges."""

    def __init__(
        self,
        node_id: str,
        node_type: str,
        node_obj: object,
        edges: list[BaseGraphEdge] | None = None,
    ) -> None:
        super().__init__(node_id=node_id, node_type=node_type, label=node_id, properties={}, node_obj=node_obj)
        object.__setattr__(self, "_edges", list(edges or []))

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """The edges given at construction."""
        return list(self._edges)


class _Inspector(BaseGraphNodeInspector[_Axis]):
    """Contribute a fixed list of nodes as the axis root's companions."""

    def __init__(self, nodes: list[BaseGraphNode[Any]]) -> None:
        self._nodes = nodes

    def get_graph_nodes(self) -> list[BaseGraphNode[Any]]:
        """Every node of the harness."""
        return list(self._nodes)

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        """Unused: :meth:`get_graph_nodes` is overridden."""
        return None


def _build(*nodes: BaseGraphNode[Any]) -> None:
    """Build a graph of the application plus ``nodes``."""
    application = _FixedGraphNode("app.Application", "Application", object())
    NodeGraphCoordinator().build([_Inspector([application, *nodes])])


def _resource_node(*targets: type) -> _FixedGraphNode:
    """A ``Resource`` node of ``_ShopDatabaseStorage`` carrying one edge per given target."""
    return _FixedGraphNode(
        TypeIntrospection.full_qualname(_ShopDatabaseStorage),
        "Resource",
        _ShopDatabaseStorage,
        [ResourceEntityGraphEdge(target) for target in targets],
    )


def test_a_listed_entity_without_a_resource_entity_edge_is_refused() -> None:
    """One entry of ``@entities`` has no edge: the coordinator names the resource and the entity."""
    with pytest.raises(
        InvalidGraphError,
        match=r"lists _ProductCoreEntity in @entities but has no resource_entity edge",
    ):
        _build(
            _resource_node(_OrderCoreEntity),
            _FixedGraphNode(TypeIntrospection.full_qualname(_OrderCoreEntity), "Entity", _OrderCoreEntity),
            _FixedGraphNode(TypeIntrospection.full_qualname(_ProductCoreEntity), "Entity", _ProductCoreEntity),
        )


def test_a_resource_entity_edge_that_ends_elsewhere_is_refused() -> None:
    """The edge is present, but its target node is not an entity: the coordinator refuses it."""
    with pytest.raises(InvalidGraphError, match=r"a Domain node, not an entity node"):
        _build(
            _resource_node(_OrderCoreEntity, _ProductCoreEntity),
            _FixedGraphNode(TypeIntrospection.full_qualname(_OrderCoreEntity), "Entity", _OrderCoreEntity),
            _FixedGraphNode(TypeIntrospection.full_qualname(_ProductCoreEntity), "Domain", _ProductCoreEntity),
        )


# ── A built graph: the edges the nodes describe ───────────────────────────────────────


_MODEL = textwrap.dedent(
    """
    import json

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.entities import entities
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources import BaseGateway, BaseStorage


    class StoreDomain(BaseDomain):
        name = "store"
        description = "Store"


    class CatalogDomain(BaseDomain):
        name = "catalog"
        description = "Catalog"


    class BillingDomain(BaseDomain):
        name = "billing"
        description = "Billing"


    class MessagingDomain(BaseDomain):
        name = "messaging"
        description = "Messaging"


    @entity(description="Customer order", domain=StoreDomain)
    class OrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    @entity(description="Product", domain=CatalogDomain)
    class ProductCoreEntity(BaseCoreEntity):
        id: str = Field(description="Product id")


    @entity(description="Payment event", domain=BillingDomain)
    class PaymentEventLogCoreEntity(BaseCoreEntity):
        id: str = Field(description="Event id")


    @entity(description="Recipient device seen", domain=MessagingDomain)
    class RecipientDeviceSeenCoreEntity(BaseCoreEntity):
        id: str = Field(description="Seen id")


    @meta(description="The shop database")
    @entities(OrderCoreEntity, ProductCoreEntity)
    class ShopDatabaseStorage(BaseStorage):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @meta(description="The catalog gateway")
    @entities(ProductCoreEntity)
    class CatalogGateway(BaseGateway):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @meta(description="The card network gateway")
    @entities(PaymentEventLogCoreEntity)
    class CardNetworkGateway(BaseGateway):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @meta(description="The notification gateway")
    @entities(RecipientDeviceSeenCoreEntity)
    class NotificationGateway(BaseGateway):
        @classmethod
        def get_wrapper_class(cls):
            return None


    print(create_node_graph_coordinator().to_json())
    """
)

_EXPECTED: dict[str, set[str]] = {
    "ShopDatabaseStorage": {"OrderCoreEntity", "ProductCoreEntity"},
    "CatalogGateway": {"ProductCoreEntity"},
    "CardNetworkGateway": {"PaymentEventLogCoreEntity"},
    "NotificationGateway": {"RecipientDeviceSeenCoreEntity"},
}


@pytest.fixture(scope="module")
def built() -> dict[str, Any]:
    """The graph of two databases and two gateways, built in a fresh interpreter."""
    result = run_isolated_model(_MODEL)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _name(node_id: str) -> str:
    """The class name a node id ends with (a ``__main__`` class has no module prefix)."""
    return node_id.rsplit(".", 1)[-1]


def _edges(built: dict[str, Any], edge_type: str, source: str) -> list[dict[str, Any]]:
    """Edges of one type leaving the class named ``source``."""
    return [
        edge
        for edge in built["edges"]
        if edge["type"] == edge_type and _name(edge["source_id"]) == source
    ]


def test_each_listed_entity_gets_its_own_resource_entity_edge(built: dict[str, Any]) -> None:
    """Every resource reaches exactly the entities its own ``@entities`` lists, one edge each."""
    reached = {
        resource: {_name(edge["target_id"]) for edge in _edges(built, "resource_entity", resource)}
        for resource in _EXPECTED
    }
    assert reached == _EXPECTED
    assert len([edge for edge in built["edges"] if edge["type"] == "resource_entity"]) == sum(
        len(targets) for targets in _EXPECTED.values()
    )


def test_the_two_gateways_list_the_entities_they_answer_with(built: dict[str, Any]) -> None:
    """A gateway is a database too: the card network and notification gateways reach their entities."""
    assert {_name(edge["target_id"]) for edge in _edges(built, "resource_entity", "CardNetworkGateway")} == {
        "PaymentEventLogCoreEntity"
    }
    assert {_name(edge["target_id"]) for edge in _edges(built, "resource_entity", "NotificationGateway")} == {
        "RecipientDeviceSeenCoreEntity"
    }


def test_one_entity_may_be_listed_by_two_databases(built: dict[str, Any]) -> None:
    """The same product lies in the shop database and in the catalog gateway: two edges, no refusal."""
    sources = {
        _name(edge["source_id"])
        for edge in built["edges"]
        if edge["type"] == "resource_entity" and _name(edge["target_id"]) == "ProductCoreEntity"
    }
    assert sources == {"ShopDatabaseStorage", "CatalogGateway"}


def test_a_resource_has_no_domain_edge(built: dict[str, Any]) -> None:
    """No ``domain`` edge leaves a resource: its domains are the domains of its entities."""
    resource_names = {node["label"] for node in built["nodes"] if node["type"] == "Resource"}
    assert {_name(edge["source_id"]) for edge in built["edges"] if edge["type"] == "domain"}.isdisjoint(
        resource_names
    )


def test_every_entity_keeps_its_own_domain_edge(built: dict[str, Any]) -> None:
    """Each entity reaches the domain it declares, and that domain is what the resource shares."""
    domain_of = {
        _name(edge["source_id"]): _name(edge["target_id"])
        for edge in built["edges"]
        if edge["type"] == "domain"
    }
    assert domain_of["OrderCoreEntity"] == "StoreDomain"
    assert domain_of["ProductCoreEntity"] == "CatalogDomain"
    assert domain_of["PaymentEventLogCoreEntity"] == "BillingDomain"
    assert domain_of["RecipientDeviceSeenCoreEntity"] == "MessagingDomain"


def test_every_resource_entity_row_is_an_aggregation_with_the_default_id(built: dict[str, Any]) -> None:
    """The built rows match protocol 2.0's ``resource_entity`` branch, ids included."""
    rows = [edge for edge in built["edges"] if edge["type"] == "resource_entity"]
    assert rows
    for row in rows:
        assert row["relationship"] == "Aggregation"
        assert row["is_dag"] is True
        assert row["properties"] == {}
        assert row["id"] == f"{row['source_id']}|resource_entity|{row['target_id']}"


def test_the_graph_is_protocol_2_0_and_validates(built: dict[str, Any]) -> None:
    """The document names 2.0 and validates against AOA's copy of the protocol's schema."""
    assert built["schema_version"] == "2.0"
    jsonschema.Draft202012Validator(GRAPH_JSON_SCHEMA).validate(built)
