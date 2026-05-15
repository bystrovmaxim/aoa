# tests/graph/test_dag_unit.py

"""Contract tests for the interchange structural DAG slice (``DEPENDS_ON`` / ``CONNECTS_TO``, ``is_dag``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from aoa.graph import GraphEdge
from aoa.graph._dag import is_dag_slice_acyclic

_DAG_EDGE_SLICE = frozenset({"DEPENDS_ON", "CONNECTS_TO"})


def _collect_dag_edge_pairs(edges: Sequence[GraphEdge]) -> list[tuple[str, str]]:
    acc: set[tuple[str, str]] = set()
    for e in edges:
        if e.edge_type not in _DAG_EDGE_SLICE or not e.is_dag:
            continue
        acc.add((e.source_id, e.target_id))
    return sorted(acc)


def _v(vid: str) -> dict[str, object]:
    return {
        "id": vid,
        "node_type": "Action",
        "label": vid,
        "properties": {},
        "links": [],
    }


def _dag_subgraph_is_acyclic(
    vertices: Sequence[Mapping[str, object]],
    edges: Sequence[GraphEdge],
) -> tuple[bool, list[tuple[str, str]]]:
    pairs = _collect_dag_edge_pairs(edges)
    if not pairs:
        return True, pairs
    ids = {str(v["id"]) for v in vertices}
    for s, t in pairs:
        if s not in ids or t not in ids:
            msg = f"DAG edge references unknown graph node: {(s, t)!r}"
            raise ValueError(msg)
    ordered = sorted(ids)
    adj: dict[str, list[str]] = {vid: [] for vid in ordered}
    for s, t in pairs:
        adj[s].append(t)
    return is_dag_slice_acyclic(adj, ordered), pairs


@pytest.mark.graph_coverage
def test_dag_slice_pair_collector_filters_non_dag_edges() -> None:
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
    assert _collect_dag_edge_pairs(edges) == [("x", "y")]


@pytest.mark.graph_coverage
def test_dag_subgraph_detects_three_node_cycle() -> None:
    vertices = [_v("a"), _v("b"), _v("c")]
    edges = [
        GraphEdge("a", "b", "DEPENDS_ON", "Serving", "direct", True, {}),
        GraphEdge("b", "c", "DEPENDS_ON", "Serving", "direct", True, {}),
        GraphEdge("c", "a", "DEPENDS_ON", "Serving", "direct", True, {}),
    ]
    ok, pairs = _dag_subgraph_is_acyclic(vertices, edges)
    assert not ok
    assert len(pairs) == 3


@pytest.mark.graph_coverage
def test_dag_slice_chain_then_cycle_detected() -> None:
    vertices = [_v("a"), _v("b"), _v("c")]
    edges_acyclic = [
        GraphEdge("a", "b", "DEPENDS_ON", "Serving", "direct", True, {}),
        GraphEdge("b", "c", "DEPENDS_ON", "Serving", "direct", True, {}),
    ]
    assert _collect_dag_edge_pairs(edges_acyclic) == [("a", "b"), ("b", "c")]
    ok, _pairs = _dag_subgraph_is_acyclic(vertices, edges_acyclic)
    assert ok

    edges_cyclic = [
        *edges_acyclic,
        GraphEdge("c", "a", "DEPENDS_ON", "Serving", "direct", True, {}),
    ]
    ok2, _pairs2 = _dag_subgraph_is_acyclic(vertices, edges_cyclic)
    assert not ok2
