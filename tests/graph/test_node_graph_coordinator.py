# tests/graph/test_node_graph_coordinator.py
"""Tests for :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pytest

from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.exceptions import DuplicateNodeError, InvalidGraphError
from graph.exclude_graph_model import exclude_graph_model, excluded_from_graph_model
from graph.node_graph_coordinator import NodeGraphCoordinator


class _GraphInspectorTestRoot:
    """Module-level axis type for :class:`_NodeGraphTestInspector` specialization."""


def _edge(
    source_node_id: str,
    target_node_id: str,
    *,
    edge_name: str = "ref",
    is_dag: bool = False,
) -> BaseGraphEdge:
    return AssociationGraphEdge(
        edge_name=edge_name,
        is_dag=is_dag,
        source=source_node_id,
        target_node_id=target_node_id,
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
    edge = _edge("a", "b")
    b = _make_node("b", [])
    a = _make_node("a", [edge])
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
    assert edge.source_node is a
    assert edge.target_node is b


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


def test_missing_source_raises() -> None:
    a = _make_node("a", [_edge("missing", "a")])
    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match="missing source_node_id"):
        coord.build([_NodeGraphTestInspector([a])])


def test_host_may_list_edges_whose_logical_source_is_a_companion() -> None:
    """Hosts with :meth:`BaseGraphNode.allows_companion_sourced_outgoing_edges` reuse companion ids as ``source_node_id``."""

    lc = "billing.Entity:lifecycle:lifecycle"
    nid_s = f"{lc}:recorded"
    nid_t = f"{lc}:settled"
    e = AssociationGraphEdge(
        edge_name="lifecycle_transition",
        is_dag=False,
        source=nid_s,
        target_node_id=nid_t,
    )

    class _LifecycleHost(BaseGraphNode[object]):
        def __init__(self, edges: list[BaseGraphEdge]) -> None:
            self._edges = edges
            super().__init__(
                node_id=lc,
                node_type="LifeCycle",
                label="lifecycle",
                properties={},
                node_obj=object(),
            )

        def get_all_edges(self) -> list[BaseGraphEdge]:
            return self._edges

        def allows_companion_sourced_outgoing_edges(self) -> bool:
            return True

    n_s = _make_node(nid_s, [])
    n_t = _make_node(nid_t, [])
    host = _LifecycleHost([e])
    coord = NodeGraphCoordinator()
    coord.build([_NodeGraphTestInspector([host, n_s, n_t])])
    assert coord.rx_graph.num_nodes() == 3
    assert coord.rx_graph.num_edges() == 1
    assert e.source_node is n_s and e.target_node is n_t


def test_aggregate_companion_sources_rejects_ids_outside_host_prefix() -> None:
    lc = "pkg:lc"
    e = AssociationGraphEdge(
        edge_name="lifecycle_transition",
        is_dag=False,
        source="other:s",
        target_node_id=f"{lc}:t",
    )

    class _LifecycleHost(BaseGraphNode[object]):
        def __init__(self) -> None:
            self._edges = [e]
            super().__init__(
                node_id=lc,
                node_type="LifeCycle",
                label="lc",
                properties={},
                node_obj=object(),
            )

        def get_all_edges(self) -> list[BaseGraphEdge]:
            return self._edges

        def allows_companion_sourced_outgoing_edges(self) -> bool:
            return True

    host = _LifecycleHost()
    n_o = _make_node("other:s", [])
    n_t = _make_node(f"{lc}:t", [])
    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match=r"outside namespace"):
        coord.build([_NodeGraphTestInspector([host, n_o, n_t])])


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


def test_external_service_scaffold_has_exclude_graph_model_subclasses_do_not_inherit_marker() -> None:
    from action_machine.resources.external_service.external_service_resource import (
        ExternalServiceResource,
    )

    class _Subbed(ExternalServiceResource[object]):
        pass

    assert excluded_from_graph_model(ExternalServiceResource)
    assert not excluded_from_graph_model(_Subbed)


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


def test_get_graph_nodes_skips_only_exclude_graph_model_hosts() -> None:
    """Abstract axis stubs omit interchange rows only when marked ``exclude_graph_model``."""

    class _Axis:
        pass

    @exclude_graph_model
    class _AbstractMid(_Axis, ABC):
        @abstractmethod
        def _marker(self) -> None:
            """Subclass contract."""

    class _Concrete(_AbstractMid):
        def _marker(self) -> None:
            return None

    n_axis = _make_node("axis", [])
    n_concrete = _make_node("concrete", [])

    class _Inspector(BaseGraphNodeInspector[_Axis]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            if cls is _Axis:
                return n_axis
            if cls is _Concrete:
                return n_concrete
            raise AssertionError(f"unexpected cls {cls!r}")

    assert _Inspector().get_graph_nodes() == [n_axis, n_concrete]
