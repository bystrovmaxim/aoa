# src/action_machine/graph/logical/logical_dag.py

"""
DAG validation for the **logical** graph (``graph.md`` §6).

Only edges whose ``edge_type`` is in ``DAG_EDGE_TYPES`` and whose ``is_dag`` flag is
``True`` participate — mirroring the facet coordinator policy of checking structural
(dependency) edges only, while ignoring informational / reverse projections.
"""

from __future__ import annotations

from collections.abc import Sequence

import rustworkx as rx

from action_machine.graph.exceptions import InvalidGraphError
from action_machine.graph.logical.constants import DAG_EDGE_TYPES
from action_machine.graph.logical.model import LogicalEdge, LogicalVertex


def collect_logical_dag_edge_pairs(edges: Sequence[LogicalEdge]) -> list[tuple[str, str]]:
    """
    Return sorted unique ``(source_id, target_id)`` pairs for logical DAG edges.

    Includes only edges with ``edge_type in DAG_EDGE_TYPES`` and ``is_dag is True``.
    """
    acc: set[tuple[str, str]] = set()
    for e in edges:
        if e.edge_type not in DAG_EDGE_TYPES or not e.is_dag:
            continue
        acc.add((e.source_id, e.target_id))
    return sorted(acc)


def logical_dag_subgraph_is_acyclic(
    vertices: Sequence[LogicalVertex],
    edges: Sequence[LogicalEdge],
) -> tuple[bool, list[tuple[str, str]]]:
    """
    Return ``(is_acyclic, dag_edge_pairs)`` for the logical DAG slice.

    Empty DAG edge list is treated as acyclic. Raises ``ValueError`` if a DAG edge
    references a vertex id missing from ``vertices``.
    """
    pairs = collect_logical_dag_edge_pairs(edges)
    if not pairs:
        return True, pairs
    ids = {v.id for v in vertices}
    for s, t in pairs:
        if s not in ids or t not in ids:
            msg = f"DAG edge references unknown vertex: {(s, t)!r}"
            raise ValueError(msg)
    g = rx.PyDiGraph()
    idx = {vid: g.add_node(vid) for vid in sorted(ids)}
    for s, t in pairs:
        g.add_edge(idx[s], idx[t], None)
    return rx.is_directed_acyclic_graph(g), pairs


def assert_logical_dag_edges_acyclic(
    vertices: Sequence[LogicalVertex],
    edges: Sequence[LogicalEdge],
) -> list[tuple[str, str]]:
    """
    Raise ``InvalidGraphError`` when logical DAG edges form a directed cycle.

    Returns the canonical sorted DAG edge pair list (possibly empty).
    """
    ok, pairs = logical_dag_subgraph_is_acyclic(vertices, edges)
    if not ok:
        raise InvalidGraphError(
            "Logical dependency edges (DEPENDS_ON / CONNECTS_TO with is_dag=True) "
            f"form a cycle. Canonical edge list: {pairs!r}",
        )
    return pairs


def logical_dag_edge_pairs_from_rx(lg: rx.PyDiGraph) -> list[tuple[str, str]]:
    """Collect DAG edge pairs from a committed logical ``PyDiGraph`` (same rules)."""
    id_by_idx = {i: lg[i]["id"] for i in lg.node_indices()}
    acc: set[tuple[str, str]] = set()
    for s, t, w in lg.weighted_edge_list():
        if w["edge_type"] not in DAG_EDGE_TYPES or not w["is_dag"]:
            continue
        acc.add((id_by_idx[s], id_by_idx[t]))
    return sorted(acc)


def logical_dag_subgraph_is_acyclic_from_rx(lg: rx.PyDiGraph) -> bool:
    """Return whether the DAG slice of ``lg`` is acyclic (``True`` when empty)."""
    pairs = logical_dag_edge_pairs_from_rx(lg)
    if not pairs:
        return True
    ids: set[str] = set()
    for s, t in pairs:
        ids.add(s)
        ids.add(t)
    g = rx.PyDiGraph()
    idx = {vid: g.add_node(vid) for vid in sorted(ids)}
    for s, t in pairs:
        g.add_edge(idx[s], idx[t], None)
    return rx.is_directed_acyclic_graph(g)
