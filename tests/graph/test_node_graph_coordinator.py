# tests/graph/test_node_graph_coordinator.py
"""Tests for :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`."""

from __future__ import annotations

import pytest

from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import ASSOCIATION
from graph.exceptions import DuplicateNodeError, InvalidGraphError
from graph.node_graph_coordinator import NodeGraphCoordinator
from graph.base_node_graph_inspector import BaseNodeGraphInspector


def _edge(
    source_node_id: str,
    target_node_id: str,
    *,
    edge_name: str = "ref",
    is_dag: bool = False,
) -> BaseGraphEdge:
    return BaseGraphEdge(
        edge_name=edge_name,
        is_dag=is_dag,
        source_node_id=source_node_id,
        source_node_type="Test",
        source_node_obj=object(),
        target_node_id=target_node_id,
        target_node_type="Test",
        target_node_obj=object(),
        edge_relationship=ASSOCIATION,
    )


def _make_node(
    node_id: str,
    edge_list: list[BaseGraphEdge],
) -> BaseGraphNode[object]:
    """Minimal interchange node with a fixed id (closure over ``node_id``)."""

    class _N(BaseGraphNode[object]):
        def __init__(self, obj: object) -> None:
            super().__init__(
                node_id=node_id,
                node_type="Test",
                label="L",
                properties={},
                edges=list(edge_list),
                node_obj=obj,
            )

    return _N(object())


class _NodeGraphTestInspector(BaseNodeGraphInspector):
    """Test-only :class:`BaseNodeGraphInspector` stub."""

    def __init__(self, nodes: list[BaseGraphNode[object]]) -> None:
        self._nodes = nodes

    def get_graph_nodes(self) -> list[BaseGraphNode[object]]:
        return list(self._nodes)


def test_node_graph_coordinator_builds_chain() -> None:
    b = _make_node("b", [])
    a = _make_node("a", [_edge("a", "b")])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([a, b])])
    assert coord._built


def test_duplicate_node_id_raises() -> None:
    n1 = _make_node("x", [])
    n2 = _make_node("x", [])
    coord = NodeGraphCoordinator()
    with pytest.raises(DuplicateNodeError, match="x"):
        coord.build(
            [
                _NodeGraphTestInspector([n1]),
                _NodeGraphTestInspector([n2]),
            ],
        )


def test_missing_target_raises() -> None:
    a = _make_node("a", [_edge("a", "missing")])
    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match="missing"):
        coord.build([_NodeGraphTestInspector([a])])


def test_dag_cycle_raises() -> None:
    a = _make_node("a", [_edge("a", "b", is_dag=True)])
    b = _make_node("b", [_edge("b", "a", is_dag=True)])
    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match="cycle"):
        coord.build([_NodeGraphTestInspector([a, b])])


def test_non_dag_cycle_allowed() -> None:
    a = _make_node("a", [_edge("a", "b", is_dag=False)])
    b = _make_node("b", [_edge("b", "a", is_dag=False)])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([a, b])])
    assert coord._built


def test_build_twice_raises() -> None:
    n = _make_node("a", [])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([n])])
    with pytest.raises(RuntimeError, match="already"):
        coord.build([_NodeGraphTestInspector([n])])


def test_build_accepts_base_node_graph_inspector_instances() -> None:
    n = _make_node("a", [])
    insp = _NodeGraphTestInspector([n])
    assert isinstance(insp, BaseNodeGraphInspector)
