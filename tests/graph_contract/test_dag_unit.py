# tests/graph_contract/test_dag_unit.py

"""Unit tests for interchange DAG slice helpers (``action_machine.graph.dag``)."""

from __future__ import annotations

import pytest
import rustworkx as rx

from action_machine.graph import (
    GraphEdge,
    GraphVertex,
    assert_dag_edges_acyclic,
    collect_dag_edge_pairs,
    dag_edge_pairs_from_rx,
    dag_subgraph_is_acyclic,
    dag_subgraph_is_acyclic_from_rx,
)
from action_machine.graph.exceptions import InvalidGraphError


def _v(vid: str) -> GraphVertex:
    return GraphVertex(
        id=vid,
        node_type="Action",
        stereotype="Business Process",
        label=vid,
        class_ref=None,
        properties={},
    )


@pytest.mark.graph_coverage
def test_collect_dag_edge_pairs_filters_non_dag_types() -> None:
    edges = [
        GraphEdge(
            "a",
            "b",
            "BELONGS_TO",
            "Aggregation",
            "direct",
            False,
            {},
        ),
        GraphEdge(
            "x",
            "y",
            "DEPENDS_ON",
            "Serving",
            "direct",
            True,
            {},
        ),
    ]
    assert collect_dag_edge_pairs(edges) == [("x", "y")]


@pytest.mark.graph_coverage
def test_dag_subgraph_detects_three_node_cycle() -> None:
    vertices = [_v("a"), _v("b"), _v("c")]
    edges = [
        GraphEdge("a", "b", "DEPENDS_ON", "Serving", "direct", True, {}),
        GraphEdge("b", "c", "DEPENDS_ON", "Serving", "direct", True, {}),
        GraphEdge("c", "a", "DEPENDS_ON", "Serving", "direct", True, {}),
    ]
    ok, pairs = dag_subgraph_is_acyclic(vertices, edges)
    assert not ok
    assert len(pairs) == 3


@pytest.mark.graph_coverage
def test_assert_dag_edges_acyclic_raises_on_cycle() -> None:
    vertices = [_v("a"), _v("b"), _v("c")]
    edges = [
        GraphEdge("a", "b", "DEPENDS_ON", "Serving", "direct", True, {}),
        GraphEdge("b", "c", "DEPENDS_ON", "Serving", "direct", True, {}),
        GraphEdge("c", "a", "DEPENDS_ON", "Serving", "direct", True, {}),
    ]
    with pytest.raises(InvalidGraphError, match="cycle"):
        assert_dag_edges_acyclic(vertices, edges)


@pytest.mark.graph_coverage
def test_dag_subgraph_is_acyclic_from_rx_empty_and_chain() -> None:
    g = rx.PyDiGraph()
    i0 = g.add_node({"id": "a", "node_type": "Action"})
    i1 = g.add_node({"id": "b", "node_type": "Action"})
    i2 = g.add_node({"id": "c", "node_type": "Action"})
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
    assert dag_edge_pairs_from_rx(g) == [("a", "b"), ("b", "c")]
    assert dag_subgraph_is_acyclic_from_rx(g) is True

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
    assert dag_subgraph_is_acyclic_from_rx(g) is False
