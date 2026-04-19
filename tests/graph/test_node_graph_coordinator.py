# tests/graph/test_node_graph_coordinator.py
"""Tests for :class:`~action_machine.graph.node_graph_coordinator.NodeGraphCoordinator`."""

from __future__ import annotations

import pytest

from action_machine.graph.base_graph_edge import BaseGraphEdge
from action_machine.graph.base_graph_node import BaseGraphNode, Payload
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.exceptions import DuplicateNodeError, InvalidGraphError
from action_machine.graph.facet_vertex import FacetVertex
from action_machine.graph.node_graph_coordinator import NodeGraphCoordinator


def _edge(
    target_id: str,
    *,
    link_name: str = "ref",
    is_dag: bool = False,
) -> BaseGraphEdge:
    return BaseGraphEdge(
        link_name=link_name,
        target_id=target_id,
        target_node_type="Test",
        is_dag=is_dag,
        target_cls=object,
    )


def _make_node(
    node_id: str,
    edge_list: list[BaseGraphEdge],
) -> BaseGraphNode[object]:
    """Minimal interchange node with a fixed id (closure over ``node_id``)."""

    class _N(BaseGraphNode[object]):
        @classmethod
        def parse(cls, obj: object) -> Payload:
            return Payload(
                id=node_id,
                node_type="Test",
                label="L",
                properties={},
                edges=list(edge_list),
            )

    return _N(object())


class _NodeGraphProbeIntent:
    """Unused marker for :attr:`_NodeGraphTestInspector._target_intent`."""


class _NodeGraphTestInspector(BaseIntentInspector):
    """Test-only :class:`BaseIntentInspector` that only implements :meth:`get_graph_nodes`."""

    _target_intent = _NodeGraphProbeIntent

    def __init__(self, nodes: list[BaseGraphNode[object]]) -> None:
        self._nodes = nodes

    @classmethod
    def inspect(cls, target_cls: type) -> None:
        return None

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        raise NotImplementedError("test stub")

    def get_graph_nodes(self) -> list[BaseGraphNode[object]]:
        return list(self._nodes)


def test_node_graph_coordinator_builds_chain() -> None:
    b = _make_node("b", [])
    a = _make_node("a", [_edge("b")])
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
    a = _make_node("a", [_edge("missing")])
    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match="missing"):
        coord.build([_NodeGraphTestInspector([a])])


def test_dag_cycle_raises() -> None:
    a = _make_node("a", [_edge("b", is_dag=True)])
    b = _make_node("b", [_edge("a", is_dag=True)])
    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match="cycle"):
        coord.build([_NodeGraphTestInspector([a, b])])


def test_non_dag_cycle_allowed() -> None:
    a = _make_node("a", [_edge("b", is_dag=False)])
    b = _make_node("b", [_edge("a", is_dag=False)])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([a, b])])
    assert coord._built


def test_build_twice_raises() -> None:
    n = _make_node("a", [])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([n])])
    with pytest.raises(RuntimeError, match="already"):
        coord.build([_NodeGraphTestInspector([n])])


def test_build_accepts_base_intent_inspector_instances() -> None:
    n = _make_node("a", [])
    insp = _NodeGraphTestInspector([n])
    assert isinstance(insp, BaseIntentInspector)
