# tests/graph_contract/test_dag_unit.py

"""Contract tests for the interchange structural DAG slice (``DEPENDS_ON`` / ``CONNECTS_TO``, ``is_dag``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest
import rustworkx as rx

from aoa.graph import GraphEdge

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
    g = rx.PyDiGraph()
    idx = {vid: g.add_node(vid) for vid in sorted(ids)}
    for s, t in pairs:
        g.add_edge(idx[s], idx[t], None)
    return rx.is_directed_acyclic_graph(g), pairs


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


def _dag_pairs_from_rx(lg: rx.PyDiGraph) -> list[tuple[str, str]]:
    """Structural slice: edges in ``_DAG_EDGE_SLICE`` with ``is_dag``."""

    id_by_idx = {i: lg[i]["id"] for i in lg.node_indices()}
    acc: set[tuple[str, str]] = set()
    for s, t, w in lg.weighted_edge_list():
        if w["edge_type"] not in _DAG_EDGE_SLICE or not w["is_dag"]:
            continue
        acc.add((str(id_by_idx[s]), str(id_by_idx[t])))
    return sorted(acc)


def _dag_slice_acyclic_from_rx_graph(lg: rx.PyDiGraph) -> bool:
    ids = sorted({str(lg[i]["id"]) for i in lg.node_indices()})
    vertices = [_v(pid) for pid in ids]
    pairs = _dag_pairs_from_rx(lg)
    edges = [
        GraphEdge(s, t, "DEPENDS_ON", "Serving", "direct", True, {})
        for s, t in pairs
    ]
    ok, _pairs = _dag_subgraph_is_acyclic(vertices, edges)
    return ok


@pytest.mark.graph_coverage
def test_rx_commit_graph_dag_slice_chain_then_cycle_detected() -> None:
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
            "properties": {},
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
            "properties": {},
        },
    )
    assert _dag_pairs_from_rx(g) == [("a", "b"), ("b", "c")]
    assert _dag_slice_acyclic_from_rx_graph(g) is True

    g.add_edge(
        i2,
        i0,
        {
            "edge_type": "DEPENDS_ON",
            "category": "direct",
            "is_dag": True,
            "stereotype": "Serving",
            "properties": {},
        },
    )
    assert _dag_slice_acyclic_from_rx_graph(g) is False
