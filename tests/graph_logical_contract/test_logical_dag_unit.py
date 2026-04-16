# tests/graph_logical_contract/test_logical_dag_unit.py

"""Unit tests for logical DAG slice helpers (``logical_dag`` module)."""

from __future__ import annotations

import pytest
import rustworkx as rx

from action_machine.graph.exceptions import InvalidGraphError
from action_machine.graph.logical import (
    LogicalEdge,
    LogicalVertex,
    assert_logical_dag_edges_acyclic,
    collect_logical_dag_edge_pairs,
    logical_dag_edge_pairs_from_rx,
    logical_dag_subgraph_is_acyclic,
    logical_dag_subgraph_is_acyclic_from_rx,
)


def _v(vid: str) -> LogicalVertex:
    return LogicalVertex(
        id=vid,
        vertex_type="action",
        stereotype="Business Process",
        display_name=vid,
        class_ref=None,
        properties={},
    )


@pytest.mark.graph_coverage
def test_collect_logical_dag_edge_pairs_filters_non_dag_types() -> None:
    edges = [
        LogicalEdge(
            "a",
            "b",
            "BELONGS_TO",
            "Aggregation",
            "direct",
            False,
            {},
        ),
        LogicalEdge(
            "x",
            "y",
            "DEPENDS_ON",
            "Serving",
            "direct",
            True,
            {},
        ),
    ]
    assert collect_logical_dag_edge_pairs(edges) == [("x", "y")]


@pytest.mark.graph_coverage
def test_logical_dag_subgraph_detects_three_node_cycle() -> None:
    vertices = [_v("a"), _v("b"), _v("c")]
    edges = [
        LogicalEdge("a", "b", "DEPENDS_ON", "Serving", "direct", True, {}),
        LogicalEdge("b", "c", "DEPENDS_ON", "Serving", "direct", True, {}),
        LogicalEdge("c", "a", "DEPENDS_ON", "Serving", "direct", True, {}),
    ]
    ok, pairs = logical_dag_subgraph_is_acyclic(vertices, edges)
    assert not ok
    assert len(pairs) == 3


@pytest.mark.graph_coverage
def test_assert_logical_dag_edges_acyclic_raises_on_cycle() -> None:
    vertices = [_v("a"), _v("b"), _v("c")]
    edges = [
        LogicalEdge("a", "b", "DEPENDS_ON", "Serving", "direct", True, {}),
        LogicalEdge("b", "c", "DEPENDS_ON", "Serving", "direct", True, {}),
        LogicalEdge("c", "a", "DEPENDS_ON", "Serving", "direct", True, {}),
    ]
    with pytest.raises(InvalidGraphError, match="cycle"):
        assert_logical_dag_edges_acyclic(vertices, edges)


@pytest.mark.graph_coverage
def test_logical_dag_subgraph_is_acyclic_from_rx_empty_and_chain() -> None:
    g = rx.PyDiGraph()
    i0 = g.add_node({"id": "a", "vertex_type": "action"})
    i1 = g.add_node({"id": "b", "vertex_type": "action"})
    i2 = g.add_node({"id": "c", "vertex_type": "action"})
    g.add_edge(
        i0,
        i1,
        {
            "edge_type": "DEPENDS_ON",
            "category": "direct",
            "is_dag": True,
            "stereotype": "Serving",
            "attributes": {},
        },
    )
    g.add_edge(
        i1,
        i2,
        {
            "edge_type": "DEPENDS_ON",
            "category": "direct",
            "is_dag": True,
            "stereotype": "Serving",
            "attributes": {},
        },
    )
    assert logical_dag_edge_pairs_from_rx(g) == [("a", "b"), ("b", "c")]
    assert logical_dag_subgraph_is_acyclic_from_rx(g) is True

    g.add_edge(
        i2,
        i0,
        {
            "edge_type": "DEPENDS_ON",
            "category": "direct",
            "is_dag": True,
            "stereotype": "Serving",
            "attributes": {},
        },
    )
    assert logical_dag_subgraph_is_acyclic_from_rx(g) is False
