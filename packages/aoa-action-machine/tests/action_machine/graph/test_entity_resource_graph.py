# tests/action_machine/graph/test_entity_resource_graph.py
"""
Tests for the ``entity_resource`` edge and the graph build's resource rules (protocol 1.6).

A built graph carries one ``entity_resource`` edge from every entity to its resource and an
entity ``domain`` edge to that resource's domain, and validates against schema 1.7. The graph
build refuses, before a graph is indexed, an entity without exactly one such edge, and lets
every link — relation, dictionary reference, specialization, generalization, lifecycle states —
join entities of two resources. Both are driven with hand-built nodes.
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

import jsonschema
import pytest

from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA

from ...support.isolated_entity_models import run_isolated_model

_MODEL = textwrap.dedent(
    """
    import json

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources.base_storage import BaseStorage
    from aoa.action_machine.resources import InMemoryDataSource


    class StoreDomain(BaseDomain):
        name = "store"
        description = "Store"


    @meta(description="Where StorefrontDatabase keeps its rows")
    class StorefrontDataSource(InMemoryDataSource):
        pass


    @meta(description="Primary relational store", domain=StoreDomain)
    class StorefrontDatabase(BaseStorage[StorefrontDataSource]):
        pass


    @entity(description="Customer order", resource=StorefrontDatabase)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    print(create_node_graph_coordinator().to_json())
    """
)


@pytest.fixture(scope="module")
def built() -> dict[str, Any]:
    """The graph of one store database holding one order, built in a fresh interpreter."""
    result = run_isolated_model(_MODEL)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _name(node_id: str) -> str:
    """The class name a node id ends with (a ``__main__`` class has no module prefix)."""
    return node_id.rsplit(".", 1)[-1]


def _edges(graph: dict[str, Any], edge_type: str, source: str) -> list[dict[str, Any]]:
    """Edges of one type leaving the class named ``source``."""
    return [e for e in graph["edges"] if e["type"] == edge_type and _name(e["source_id"]) == source]


def test_case_2_6_the_entity_points_at_its_resource(built: dict[str, Any]) -> None:
    """One ``entity_resource`` row: Aggregation, a DAG edge, no properties, the default id."""
    (row,) = _edges(built, "entity_resource", "SalesOrderCoreEntity")
    assert _name(row["target_id"]) == "StorefrontDatabase"
    assert row["relationship"] == "Aggregation"
    assert row["is_dag"] is True
    assert row["properties"] == {}
    assert row["id"] == f"{row['source_id']}|entity_resource|{row['target_id']}"


def test_case_2_6_the_entity_domain_is_the_resource_domain(built: dict[str, Any]) -> None:
    """The entity's ``domain`` edge reaches the domain its resource declares."""
    (entity_domain,) = _edges(built, "domain", "SalesOrderCoreEntity")
    (resource_domain,) = _edges(built, "domain", "StorefrontDatabase")
    assert entity_domain["target_id"] == resource_domain["target_id"]
    assert _name(entity_domain["target_id"]) == "StoreDomain"


def test_the_graph_is_protocol_1_7(built: dict[str, Any]) -> None:
    """The document names 1.7 and validates against AOA's copy of schema 1.7."""
    assert built["schema_version"] == "1.7"
    jsonschema.Draft202012Validator(GRAPH_JSON_SCHEMA).validate(built)


# ── Hand-built nodes: the graph build's own resource rules ──────────────────────────────


class _Axis:
    """Root type of the harness inspector."""


class _Link(AssociationGraphEdge):
    """A link edge of any name; an ``entity_relation`` carries the field name its id needs."""

    def __init__(self, edge_name: str, target_id: str) -> None:
        super().__init__(edge_name=edge_name, is_dag=False, target_node_id=target_id, target_node=None)

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        """Serialize with the ``field_name`` an ``entity_relation`` id is built from."""
        properties = {"field_name": "link"} if self.edge_name == "entity_relation" else {}
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": properties,
        }


class _Node(BaseGraphNode[object]):
    """A node with a given type, properties and edges."""

    def __init__(
        self,
        node_id: str,
        node_type: str,
        edges: list[BaseGraphEdge] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(node_id=node_id, node_type=node_type, label=node_id, properties=properties or {}, node_obj=object())
        object.__setattr__(self, "_edges", edges or [])

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


def _stored(entity_id: str, resource_id: str, *links: BaseGraphEdge) -> _Node:
    """An entity node stored by ``resource_id`` with the given links."""
    return _Node(entity_id, "Entity", [_Link("entity_resource", resource_id), *links])


def _build(*nodes: BaseGraphNode[Any]) -> None:
    """Build a graph of two resources, each on a data source of its own, plus ``nodes``."""
    application = _Node("app.Application", "Application")
    sources = [_Node(f"d.{name}", "DataSource", [_Link("application", "app.Application")]) for name in ("Storefront", "Support")]
    resources = [
        _Node("r.StorefrontDatabase", "Resource", [_Link("resource_data_source", "d.Storefront")]),
        _Node("r.SupportDatabase", "Resource", [_Link("resource_data_source", "d.Support")]),
    ]
    NodeGraphCoordinator().build([_Inspector([application, *sources, *resources, *nodes])])


def test_case_2_5_an_entity_without_the_edge_is_refused() -> None:
    """Zero ``entity_resource`` edges: the build names the entity."""
    with pytest.raises(InvalidGraphError) as error:
        _build(_Node("e.Order", "Entity"))
    assert str(error.value) == "Entity e.Order has 0 entity_resource edges; an entity has exactly one."


def test_case_2_5_an_entity_with_two_edges_is_refused() -> None:
    """Two ``entity_resource`` edges: the build names the entity."""
    node = _Node(
        "e.Order",
        "Entity",
        [_Link("entity_resource", "r.StorefrontDatabase"), _Link("entity_resource", "r.SupportDatabase")],
    )
    with pytest.raises(InvalidGraphError) as error:
        _build(node)
    assert str(error.value) == "Entity e.Order has 2 entity_resource edges; an entity has exactly one."


@pytest.mark.parametrize("edge_type", ["entity_relation", "entity_reference", "entity_specialization", "parent_entity"])
def test_a_link_across_resources_builds(edge_type: str) -> None:
    """Every link kind between entities of two resources builds: a relation knows no store."""
    ticket = _stored("e.Ticket", "r.SupportDatabase", _Link(edge_type, "e.Order"))
    _build(_stored("e.Order", "r.StorefrontDatabase"), ticket)


def test_lifecycle_states_across_resources_build() -> None:
    """States of one lifecycle on entities of two resources build."""
    states = [
        _Node("e.Order:lifecycle:lifecycle:draft", "StateInitial", properties={"lifecycle_class_id": "l.OrderLifecycle"}),
        _Node("e.Ticket:lifecycle:lifecycle:draft", "StateInitial", properties={"lifecycle_class_id": "l.OrderLifecycle"}),
    ]
    _build(_stored("e.Order", "r.StorefrontDatabase"), _stored("e.Ticket", "r.SupportDatabase"), *states)


def test_links_inside_one_resource_build() -> None:
    """The same links inside one resource build."""
    ticket = _stored("e.Ticket", "r.StorefrontDatabase", _Link("entity_relation", "e.Order"))
    _build(_stored("e.Order", "r.StorefrontDatabase"), ticket)
