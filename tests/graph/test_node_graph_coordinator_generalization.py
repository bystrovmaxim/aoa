# tests/graph/test_node_graph_coordinator_generalization.py
"""PR-5: coordinator referential integrity, indexes, and JSON export for ``parent_*`` edges (plan §PR-5, §I.7)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.graph.core.generalization_graph_edge import GeneralizationGraphEdge
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator


class _Axis:
    pass


class _EdgeNode(BaseGraphNode[object]):
    def __init__(
        self,
        *,
        node_id: str,
        node_type: str = "Action",
        edges: list[BaseGraphEdge] | None = None,
        companions: list[BaseGraphNode[Any]] | None = None,
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=node_type,
            label=node_id,
            properties={"description": "fixture"},
            node_obj=object(),
        )
        object.__setattr__(self, "_edges", [] if edges is None else list(edges))
        object.__setattr__(self, "_companions", [] if companions is None else list(companions))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "properties": dict(self.properties),
        }

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return list(self._edges)

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        return list(self._companions)


def test_build_rejects_parent_action_with_missing_target_node() -> None:
    child = _EdgeNode(
        node_id="fixture.graph.Child",
        edges=[
            GeneralizationGraphEdge(
                edge_name="parent_action",
                is_dag=False,
                target_node_id="fixture.graph.MissingParent",
                target_node=None,
            ),
        ],
    )

    class _Insp(BaseGraphNodeInspector[_Axis]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            return child if cls is _Axis else None

    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match=r"parent_action.*fixture\.graph\.Child.*missing"):
        coord.build([_Insp()])


def test_build_wires_parent_action_and_indexes_and_json() -> None:
    parent = _EdgeNode(node_id="fixture.graph.Parent")
    child = _EdgeNode(
        node_id="fixture.graph.Child",
        edges=[
            GeneralizationGraphEdge(
                edge_name="parent_action",
                is_dag=False,
                target_node_id=parent.node_id,
                target_node=None,
            ),
        ],
        companions=[parent],
    )

    class _Insp(BaseGraphNodeInspector[_Axis]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            return child if cls is _Axis else None

    coord = NodeGraphCoordinator()
    coord.build([_Insp()])

    triples = coord.get_edges_by_type("parent_action")
    assert len(triples) == 1
    s_id, t_id, edge = triples[0]
    assert (s_id, t_id) == ("fixture.graph.Child", "fixture.graph.Parent")
    assert edge.edge_name == "parent_action"

    raw = coord.to_json()
    payload = json.loads(raw)
    pa = [e for e in payload["edges"] if e["type"] == "parent_action"]
    assert len(pa) == 1
    assert pa[0]["source_id"] == "fixture.graph.Child"
    assert pa[0]["target_id"] == "fixture.graph.Parent"
    assert pa[0]["relationship"] == "Generalization"
    assert pa[0]["is_dag"] is False


def test_pr8_single_node_graph_has_no_parent_generalization_edges() -> None:
    """PR-8 smoke: coordinator with one node and no ``parent_*`` edges — JSON stays consistent."""
    lone = _EdgeNode(node_id="fixture.graph.Only", edges=[])

    class _Insp(BaseGraphNodeInspector[_Axis]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            return lone if cls is _Axis else None

    coord = NodeGraphCoordinator()
    coord.build([_Insp()])
    payload = json.loads(coord.to_json())
    parentish = {e["type"] for e in payload["edges"] if e["type"] in {"parent_action", "parent_role", "parent_domain"}}
    assert not parentish
