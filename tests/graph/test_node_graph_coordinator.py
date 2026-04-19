# tests/graph/test_node_graph_coordinator.py
"""Tests for :class:`~action_machine.graph.node_graph_coordinator.NodeGraphCoordinator`."""

from __future__ import annotations

import pytest
import rustworkx as rx

from action_machine.graph.base_graph_edge import BaseGraphEdge
from action_machine.graph.base_graph_node import BaseGraphNode, Payload
from action_machine.graph.exceptions import DuplicateNodeError, InvalidGraphError
from action_machine.graph.node_graph_coordinator import GraphNodeSource, NodeGraphCoordinator


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


class _StaticInsp:
    """Inspector adapter holding a fixed list of nodes."""

    def __init__(self, nodes: list[BaseGraphNode[object]]) -> None:
        self._nodes = nodes

    def get_graph_nodes(self) -> list[BaseGraphNode[object]]:
        return list(self._nodes)


def test_node_graph_coordinator_builds_chain() -> None:
    b = _make_node("b", [])
    a = _make_node("a", [_edge("b")])
    coord = NodeGraphCoordinator()
    coord.build([_StaticInsp([a, b])])
    assert coord.is_built
    assert set(coord.nodes.keys()) == {"a", "b"}
    g = coord.get_graph()
    assert isinstance(g, rx.PyDiGraph)
    assert g.num_nodes() == 2
    assert g.num_edges() == 1
    # vertex weight is BaseGraphNode
    idx = {g[i].id: i for i in g.node_indices()}
    eid = next(iter(g.edge_indices()))
    s, t = g.get_edge_endpoints_by_index(eid)
    assert g[s] is coord.get_node("a")
    assert g[t] is coord.get_node("b")
    assert g.get_edge_data_by_index(eid) == _edge("b")


def test_duplicate_node_id_raises() -> None:
    n1 = _make_node("x", [])
    n2 = _make_node("x", [])
    coord = NodeGraphCoordinator()
    with pytest.raises(DuplicateNodeError, match="x"):
        coord.build(
            [
                _StaticInsp([n1]),
                _StaticInsp([n2]),
            ],
        )


def test_missing_target_raises() -> None:
    a = _make_node("a", [_edge("missing")])
    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match="missing"):
        coord.build([_StaticInsp([a])])


def test_dag_cycle_raises() -> None:
    a = _make_node("a", [_edge("b", is_dag=True)])
    b = _make_node("b", [_edge("a", is_dag=True)])
    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match="cycle"):
        coord.build([_StaticInsp([a, b])])


def test_non_dag_cycle_allowed() -> None:
    a = _make_node("a", [_edge("b", is_dag=False)])
    b = _make_node("b", [_edge("a", is_dag=False)])
    coord = NodeGraphCoordinator()
    coord.build([_StaticInsp([a, b])])
    assert coord.get_graph().num_edges() == 2


def test_build_twice_raises() -> None:
    n = _make_node("a", [])
    coord = NodeGraphCoordinator()
    coord.build([_StaticInsp([n])])
    with pytest.raises(RuntimeError, match="already"):
        coord.build([_StaticInsp([n])])


def test_get_node_keyerror() -> None:
    n = _make_node("only", [])
    coord = NodeGraphCoordinator()
    coord.build([_StaticInsp([n])])
    with pytest.raises(KeyError, match="nope"):
        coord.get_node("nope")


def test_graph_node_source_protocol_runtime() -> None:
    assert isinstance(_StaticInsp([]), GraphNodeSource)
