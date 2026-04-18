# src/action_machine/graph/dag.py

"""
DAG validation for the coordinator interchange graph (``graph.md`` §6).

Only edges whose ``edge_type`` is in ``DAG_EDGE_TYPES`` and whose ``is_dag`` flag is
``True`` participate — today that means **``DEPENDS_ON``** and **``CONNECTS_TO``**
(structural dependency/connection skeleton).

**Out of scope for this module:** entity–entity relation edges
(``COMPOSITION_*``, ``AGGREGATION_*``, ``ASSOCIATION_*``) are
not in ``DAG_EDGE_TYPES`` and are emitted with ``is_dag=False``. Cycles on that slice
are therefore **allowed** and never inspected here; they are informational / domain
links, not the acyclic structural DAG.
"""

from __future__ import annotations

from collections.abc import Sequence

import rustworkx as rx

from action_machine.graph.constants import DAG_EDGE_TYPES
from action_machine.graph.exceptions import InvalidGraphError
from action_machine.graph.model import GraphEdge, GraphVertex


def collect_dag_edge_pairs(edges: Sequence[GraphEdge]) -> list[tuple[str, str]]:
    """
    Return sorted unique ``(source_id, target_id)`` pairs for DAG edges.

    Includes only edges with ``edge_type in DAG_EDGE_TYPES`` and ``is_dag is True``.
    """
    acc: set[tuple[str, str]] = set()
    for e in edges:
        if e.edge_type not in DAG_EDGE_TYPES or not e.is_dag:
            continue
        acc.add((e.source_id, e.target_id))
    return sorted(acc)


def dag_subgraph_is_acyclic(
    vertices: Sequence[GraphVertex],
    edges: Sequence[GraphEdge],
) -> tuple[bool, list[tuple[str, str]]]:
    """
    Return ``(is_acyclic, dag_edge_pairs)`` for the DAG slice.

    Empty DAG edge list is treated as acyclic. Raises ``ValueError`` if a DAG edge
    references a vertex id missing from ``vertices``.
    """
    pairs = collect_dag_edge_pairs(edges)
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


def assert_dag_edges_acyclic(
    vertices: Sequence[GraphVertex],
    edges: Sequence[GraphEdge],
) -> list[tuple[str, str]]:
    """
    Raise ``InvalidGraphError`` when DAG edges form a directed cycle.

    Entity relation edges are **not** part of this check (see module docstring).

    Returns the canonical sorted DAG edge pair list (possibly empty).
    """
    ok, pairs = dag_subgraph_is_acyclic(vertices, edges)
    if not ok:
        raise InvalidGraphError(
            "Dependency edges (DEPENDS_ON / CONNECTS_TO with is_dag=True) "
            f"form a cycle. Canonical edge list: {pairs!r}",
        )
    return pairs


def dag_edge_pairs_from_rx(lg: rx.PyDiGraph) -> list[tuple[str, str]]:
    """Collect DAG edge pairs from a committed interchange ``PyDiGraph`` (same rules)."""
    id_by_idx = {i: lg[i]["id"] for i in lg.node_indices()}
    acc: set[tuple[str, str]] = set()
    for s, t, w in lg.weighted_edge_list():
        if w["edge_type"] not in DAG_EDGE_TYPES or not w["is_dag"]:
            continue
        acc.add((id_by_idx[s], id_by_idx[t]))
    return sorted(acc)


def dag_subgraph_is_acyclic_from_rx(lg: rx.PyDiGraph) -> bool:
    """Return whether the DAG slice of ``lg`` is acyclic (``True`` when empty)."""
    pairs = dag_edge_pairs_from_rx(lg)
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
