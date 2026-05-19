# tests/graph/test_node_graph_coordinator_indexes.py
"""PR-3: type/source/target indexes on ``NodeGraphCoordinator``."""

from __future__ import annotations

from typing import Any

import pytest

from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.graph.composition_graph_edge import CompositionGraphEdge
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator


class _Axis:
    pass


class _EdgeNode(BaseGraphNode[object]):
    """Minimal node with explicit outgoing edges and optional companions."""

    def __init__(
        self,
        *,
        node_id: str,
        node_type: str,
        edges: list[BaseGraphEdge] | None = None,
        companions: list[BaseGraphNode[Any]] | None = None,
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=node_type,
            label=node_id,
            node_obj=object(),
        )
        object.__setattr__(self, "_edges", [] if edges is None else list(edges))
        object.__setattr__(self, "_companions", [] if companions is None else list(companions))

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return list(self._edges)

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        return list(self._companions)


def test_indexes_raise_before_build() -> None:
    c = NodeGraphCoordinator()
    with pytest.raises(RuntimeError, match="only available after a successful build"):
        c.get_nodes_by_type("any")
    with pytest.raises(RuntimeError, match="only available after a successful build"):
        c.get_edges_by_type("any")
    with pytest.raises(RuntimeError, match="only available after a successful build"):
        c.get_available_types()


def test_empty_graph_indexes() -> None:
    class _Empty(BaseGraphNodeInspector[_Axis]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            return None

    c = NodeGraphCoordinator()
    c.build([_Empty()])

    assert c.get_nodes_by_type("missing") == ()
    assert c.get_edges_by_type("missing") == ()
    assert c.get_available_types() == {"node_types": frozenset(), "edge_types": frozenset()}


def test_get_nodes_by_type_matches_full_scan() -> None:
    a = _EdgeNode(node_id="a", node_type="A")
    root = _EdgeNode(
        node_id="root",
        node_type="R",
        edges=[
            CompositionGraphEdge(
                edge_name="to_a",
                is_dag=False,
                target_node_id=a.node_id,
                target_node=a,
            ),
        ],
        companions=[a],
    )

    class _Insp(BaseGraphNodeInspector[_Axis]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            return root if cls is _Axis else None

    c = NodeGraphCoordinator()
    c.build([_Insp()])

    by_a = c.get_nodes_by_type("A")
    assert tuple(n.node_id for n in by_a) == ("a",)
    scan = {n.node_id for n in c.get_all_nodes() if n.node_type == "A"}
    assert scan == {n.node_id for n in by_a}


def test_get_edges_by_type_and_adjacency_indexes() -> None:
    target = _EdgeNode(node_id="t", node_type="T")
    edge_slot = CompositionGraphEdge(
        edge_name="slot",
        is_dag=False,
        target_node_id=target.node_id,
        target_node=target,
    )
    root = _EdgeNode(node_id="r", node_type="R", edges=[edge_slot], companions=[target])

    class _Insp(BaseGraphNodeInspector[_Axis]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            return root if cls is _Axis else None

    c = NodeGraphCoordinator()
    c.build([_Insp()])

    av = c.get_available_types()
    assert av["node_types"] == frozenset({"R", "T"})
    assert av["edge_types"] == frozenset({"slot"})

    triples = c.get_edges_by_type("slot")
    assert len(triples) == 1
    s_id, t_id, edge = triples[0]
    assert (s_id, t_id, edge.edge_name) == ("r", "t", "slot")
    assert edge is edge_slot

    assert c._edges_by_source is not None
    assert c._edges_by_target is not None
    assert c._edges_by_source["r"] == [("t", edge_slot)]
    assert c._edges_by_target["t"] == [("r", edge_slot)]
