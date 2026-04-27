# tests/graph/test_node_graph_coordinator.py
"""Tests for :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`."""

from __future__ import annotations

from typing import Any

import pytest

from action_machine.model.graph_model.action_graph_node import ActionGraphNode
from action_machine.model.graph_model.regular_aspect_graph_node import (
    RegularAspectGraphNode,
)
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.edge_relationship import ASSOCIATION, COMPOSITION
from graph.exceptions import DuplicateNodeError, InvalidGraphError
from graph.node_graph_coordinator import NodeGraphCoordinator


class _GraphInspectorTestRoot:
    """Module-level axis type for :class:`_NodeGraphTestInspector` specialization."""


class _RegularAspectHostAction:
    @staticmethod
    def run() -> None:
        pass


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
        target_node_id=target_node_id,
        target_node_type="Test",
        edge_relationship=ASSOCIATION,
    )


def _make_node(
    node_id: str,
    edge_list: list[BaseGraphEdge],
) -> BaseGraphNode[object]:
    """Minimal interchange node with a fixed id (closure over ``node_id``)."""

    class _N(BaseGraphNode[object]):
        def __init__(self, obj: object) -> None:
            self._edges = list(edge_list)
            super().__init__(
                node_id=node_id,
                node_type="Test",
                label="L",
                properties={},
                node_obj=obj,
            )

        def get_all_edges(self) -> list[BaseGraphEdge]:
            return self._edges

    return _N(object())


class _NodeGraphTestInspector(BaseGraphNodeInspector[_GraphInspectorTestRoot]):
    """Test-only :class:`BaseGraphNodeInspector` stub (nodes only for the axis root type)."""

    def __init__(self, nodes: list[BaseGraphNode[object]]) -> None:
        self._nodes = nodes

    def _get_node(self, cls: type) -> BaseGraphNode[object] | None:
        return None

    def get_graph_nodes(self) -> list[BaseGraphNode[object]]:
        return list(self._nodes)


def test_node_graph_coordinator_builds_chain() -> None:
    b = _make_node("b", [])
    a = _make_node("a", [_edge("a", "b")])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([a, b])])
    assert coord._built
    g = coord.rx_graph
    assert g.num_nodes() == 2
    assert g.num_edges() == 1
    ids = {n.node_id for n in g.nodes()}
    assert ids == {"a", "b"}
    all_nodes = coord.get_all_nodes()
    assert [n.node_id for n in all_nodes] == ["a", "b"]
    assert all_nodes[0] is a and all_nodes[1] is b


def test_rx_graph_unavailable_before_build() -> None:
    coord = NodeGraphCoordinator()
    with pytest.raises(RuntimeError, match="rx_graph"):
        _ = coord.rx_graph


def test_get_all_nodes_unavailable_before_build() -> None:
    coord = NodeGraphCoordinator()
    with pytest.raises(RuntimeError, match="rx_graph"):
        coord.get_all_nodes()


def test_rx_graph_empty_after_build_with_no_nodes() -> None:
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([])])
    assert coord.rx_graph.num_nodes() == 0
    assert coord.rx_graph.num_edges() == 0
    assert coord.get_all_nodes() == ()


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
    assert coord.rx_graph.num_nodes() == 2
    assert coord.rx_graph.num_edges() == 2


def test_build_twice_raises() -> None:
    n = _make_node("a", [])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([n])])
    with pytest.raises(RuntimeError, match="already"):
        coord.build([_NodeGraphTestInspector([n])])


def test_build_accepts_base_graph_node_inspector_instances() -> None:
    n = _make_node("a", [])
    insp = _NodeGraphTestInspector([n])
    assert isinstance(insp, BaseGraphNodeInspector)


def test_get_node_by_id_returns_node() -> None:
    n = _make_node("a", [])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([n])])
    assert coord.get_node_by_id("a") is n


def test_get_node_by_id_raises_when_missing() -> None:
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([])])
    with pytest.raises(LookupError, match="not found"):
        coord.get_node_by_id("missing")


def test_get_node_by_id_raises_when_type_mismatches() -> None:
    n = _make_node("a", [])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([n])])
    with pytest.raises(InvalidGraphError, match="is not an Action node"):
        coord.get_node_by_id("a", ActionGraphNode.NODE_TYPE)


def test_get_regular_aspect_nodes_uses_action_edges() -> None:
    aspect_node = RegularAspectGraphNode(_RegularAspectHostAction.run)
    action_node_id = (
        f"{_RegularAspectHostAction.__module__}."
        f"{_RegularAspectHostAction.__qualname__}"
    )

    class _ActionNode(BaseGraphNode[type[_RegularAspectHostAction]]):
        def __init__(self) -> None:
            self._edges = [
                BaseGraphEdge(
                    edge_name="run",
                    is_dag=False,
                    source_node_id=action_node_id,
                    source_node_type=ActionGraphNode.NODE_TYPE,
                    target_node_id=aspect_node.node_id,
                    target_node_type=RegularAspectGraphNode.NODE_TYPE,
                    edge_relationship=COMPOSITION,
                ),
            ]
            super().__init__(
                node_id=action_node_id,
                node_type=ActionGraphNode.NODE_TYPE,
                label="_Action",
                properties={},
                node_obj=_RegularAspectHostAction,
            )

        def get_all_edges(self) -> list[BaseGraphEdge]:
            return self._edges

    action_node = _ActionNode()
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([action_node, aspect_node])])
    assert coord.get_regular_aspect_nodes(_RegularAspectHostAction) == [aspect_node]


def test_get_regular_aspect_nodes_raises_when_action_missing() -> None:
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([])])
    with pytest.raises(LookupError, match="not found"):
        coord.get_regular_aspect_nodes(_RegularAspectHostAction)


def test_get_regular_aspect_nodes_raises_when_node_is_not_action() -> None:
    class _WrongActionNode(BaseGraphNode[type[_RegularAspectHostAction]]):
        def __init__(self) -> None:
            super().__init__(
                node_id=f"{_RegularAspectHostAction.__module__}.{_RegularAspectHostAction.__qualname__}",
                node_type="Domain",
                label="_RegularAspectHostAction",
                properties={},
                node_obj=_RegularAspectHostAction,
            )

    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([_WrongActionNode()])])
    with pytest.raises(InvalidGraphError, match="not an Action node"):
        coord.get_regular_aspect_nodes(_RegularAspectHostAction)


def test_all_descendant_types_transitive_and_excludes_root() -> None:
    class _Root:
        pass

    class _Mid(_Root):
        pass

    class _Leaf(_Mid):
        pass

    class _Other(_Root):
        pass

    got = BaseGraphNodeInspector._all_descendant_types(_Root)
    assert set(got) == {_Mid, _Leaf, _Other}
    assert _Root not in got
    names = [t.__qualname__ for t in got]
    assert names == sorted(names)


def test_all_descendant_types_rejects_non_type() -> None:
    not_a_type: object = ()
    with pytest.raises(TypeError, match="root must be a type"):
        BaseGraphNodeInspector._all_descendant_types(not_a_type)  # type: ignore[arg-type]


def test_get_graph_nodes_collects_root_then_sorted_descendants() -> None:
    class _R:
        pass

    class _A(_R):
        pass

    class _B(_R):
        pass

    n_root = _make_node("root", [])
    n_a = _make_node("a", [])
    n_b = _make_node("b", [])

    class _ComposingInspector(BaseGraphNodeInspector[_R]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            if cls is _R:
                return n_root
            if cls is _A:
                return n_a
            if cls is _B:
                return n_b
            return None

    assert _ComposingInspector().get_graph_nodes() == [n_root, n_a, n_b]


