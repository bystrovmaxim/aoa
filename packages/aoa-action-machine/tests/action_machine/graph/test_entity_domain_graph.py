# tests/action_machine/graph/test_entity_domain_graph.py
"""
Tests for the entity ``domain`` edge in the graph (protocol 2.0).

A built graph carries an entity ``domain`` edge to the domain the entity declares itself and
no ``entity_resource`` edge, and validates against schema 2.0. Every link — relation,
dictionary reference, specialization, generalization, lifecycle states — joins entities of
two resources: a link knows no store.
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


    class StoreDomain(BaseDomain):
        name = "store"
        description = "Store"


    @entity(description="Customer order", domain=StoreDomain)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    print(create_node_graph_coordinator().to_json())
    """
)


@pytest.fixture(scope="module")
def built() -> dict[str, Any]:
    """The graph of one entity that names its domain, built in a fresh interpreter."""
    result = run_isolated_model(_MODEL)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _name(node_id: str) -> str:
    """The class name a node id ends with (a ``__main__`` class has no module prefix)."""
    return node_id.rsplit(".", 1)[-1]


def _edges(graph: dict[str, Any], edge_type: str, source: str) -> list[dict[str, Any]]:
    """Edges of one type leaving the class named ``source``."""
    return [e for e in graph["edges"] if e["type"] == edge_type and _name(e["source_id"]) == source]


def test_the_entity_points_at_the_domain_it_declares(built: dict[str, Any]) -> None:
    """One ``domain`` row: Aggregation, a DAG edge, no properties, the default id."""
    (row,) = _edges(built, "domain", "SalesOrderCoreEntity")
    assert _name(row["target_id"]) == "StoreDomain"
    assert row["relationship"] == "Aggregation"
    assert row["is_dag"] is True
    assert row["properties"] == {}
    assert row["id"] == f"{row['source_id']}|domain|{row['target_id']}"


def test_the_graph_has_no_entity_resource_edge(built: dict[str, Any]) -> None:
    """An entity names no resource, so no ``entity_resource`` edge is produced."""
    assert [edge for edge in built["edges"] if edge["type"] == "entity_resource"] == []


def test_the_graph_is_protocol_2_0(built: dict[str, Any]) -> None:
    """The document names 2.0 and validates against AOA's copy of schema 2.0."""
    assert built["schema_version"] == "2.0"
    jsonschema.Draft202012Validator(GRAPH_JSON_SCHEMA).validate(built)


# ── Hand-built nodes: links across resources ───────────────────────────────────────────


class _Axis:
    """Root type of the harness inspector."""


class _LinkGraphEdge(AssociationGraphEdge):
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


class _TestGraphNode(BaseGraphNode[object]):
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


def _entity(entity_id: str, *links: BaseGraphEdge) -> _TestGraphNode:
    """An entity node with the given links; an entity names no resource."""
    return _TestGraphNode(entity_id, "Entity", list(links))


def _build(*nodes: BaseGraphNode[Any]) -> None:
    """Build a graph of two resources, plus ``nodes``."""
    application = _TestGraphNode("app.Application", "Application")
    resources = [
        _TestGraphNode("r.StorefrontStorage", "Resource"),
        _TestGraphNode("r.SupportDatabase", "Resource"),
    ]
    NodeGraphCoordinator().build([_Inspector([application, *resources, *nodes])])


@pytest.mark.parametrize("edge_type", ["entity_relation", "entity_reference", "entity_specialization", "parent_entity"])
def test_a_link_across_resources_builds(edge_type: str) -> None:
    """Every link kind between entities of two resources builds: a relation knows no store."""
    ticket = _entity("e.Ticket", _LinkGraphEdge(edge_type, "e.Order"))
    _build(_entity("e.Order"), ticket)


def test_lifecycle_states_across_resources_build() -> None:
    """States of one lifecycle on entities of two resources build."""
    states = [
        _TestGraphNode("e.Order:lifecycle:lifecycle:draft", "StateInitial", properties={"lifecycle_class_id": "l.OrderLifecycle"}),
        _TestGraphNode("e.Ticket:lifecycle:lifecycle:draft", "StateInitial", properties={"lifecycle_class_id": "l.OrderLifecycle"}),
    ]
    _build(_entity("e.Order"), _entity("e.Ticket"), *states)


def test_links_inside_one_resource_build() -> None:
    """The same links inside one resource build."""
    ticket = _entity("e.Ticket", _LinkGraphEdge("entity_relation", "e.Order"))
    _build(_entity("e.Order"), ticket)
