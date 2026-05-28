# packages/aoa-action-machine/src/aoa/action_machine/graph/core/_dag.py
"""Directed slice acyclicity (``is_dag=True`` edges) via Kahn topological order and Tarjan SCC.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pure-Python checks used by :class:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator`
and :class:`~aoa.action_machine.graph.core.debug_node_graph_coordinator.DebugNodeGraphCoordinator`: whether the
subgraph formed by flagged edges is acyclic, and which concrete edges participate in cycles.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    dag_adjacency  →  is_dag_slice_acyclic  →  bool
                    DagCycleViolation list  ←  dag_cycle_violations_for(nodes)
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode


@dataclass(frozen=True)
class DagCycleViolation:
    """
    AI-CORE-BEGIN
    ROLE: Debug metadata for one ``is_dag=True`` edge inside a cyclic strongly connected slice.
    CONTRACT: ``source_node_id`` / ``target_node_id`` / ``edge_name`` match interchange wiring.
    INVARIANTS: Immutable triple; ``edge_name`` is the real slot, never a DAG-flag literal.
    AI-CORE-END
    """

    source_node_id: str
    target_node_id: str
    edge_name: str


def is_dag_slice_acyclic(dag_adjacency: dict[str, list[str]], ordered_node_ids: list[str]) -> bool:
    """Return True iff the directed multigraph implied by ``dag_adjacency`` on ``ordered_node_ids`` is acyclic."""
    if not ordered_node_ids:
        return True
    indegree: dict[str, int] = {nid: 0 for nid in ordered_node_ids}
    for source_id in ordered_node_ids:
        for target_id in dag_adjacency.get(source_id, ()):
            if target_id in indegree:
                indegree[target_id] += 1
    queue: deque[str] = deque(nid for nid in ordered_node_ids if indegree[nid] == 0)
    processed = 0
    while queue:
        nid = queue.popleft()
        processed += 1
        for target_id in dag_adjacency.get(nid, ()):
            if target_id not in indegree:
                continue
            indegree[target_id] -= 1
            if indegree[target_id] == 0:
                queue.append(target_id)
    return processed == len(ordered_node_ids)


def strongly_connected_components(
    ids: Sequence[str],
    adjacency: dict[str, list[str]],
) -> list[frozenset[str]]:
    """Tarjan SCC; ``adjacency`` lists successors for keys in ``ids``."""
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: list[frozenset[str]] = []

    def visit(node_id: str) -> None:
        nonlocal index
        indices[node_id] = index
        lowlinks[node_id] = index
        index += 1
        stack.append(node_id)
        on_stack.add(node_id)

        for target_id in adjacency[node_id]:
            if target_id not in indices:
                visit(target_id)
                lowlinks[node_id] = min(lowlinks[node_id], lowlinks[target_id])
            elif target_id in on_stack:
                lowlinks[node_id] = min(lowlinks[node_id], indices[target_id])

        if lowlinks[node_id] != indices[node_id]:
            return

        component: set[str] = set()
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.add(member)
            if member == node_id:
                break
        components.append(frozenset(component))

    for node_id in ids:
        if node_id not in indices:
            visit(node_id)
    return components


def dag_cycle_violations_for(nodes: dict[str, BaseGraphNode[Any]]) -> list[DagCycleViolation]:
    """List ``DagCycleViolation`` rows for ``is_dag`` edges inside directed cycles (debug diagnostics)."""
    ids = sorted(nodes.keys())
    if not ids:
        return []
    adjacency: dict[str, list[str]] = {nid: [] for nid in ids}
    dag_edges: list[DagCycleViolation] = []
    for source_id, node in nodes.items():
        for edge in node.get_all_edges():
            if not edge.is_dag:
                continue
            adjacency[source_id].append(edge.target_node_id)
            dag_edges.append(
                DagCycleViolation(source_id, edge.target_node_id, edge.edge_name),
            )
    if not dag_edges or is_dag_slice_acyclic(adjacency, ids):
        return []

    components = strongly_connected_components(ids, adjacency)
    component_by_id = {nid: comp for comp in components for nid in comp}
    return sorted(
        (
            edge
            for edge in dag_edges
            if edge.source_node_id == edge.target_node_id
            or (
                len(component_by_id[edge.source_node_id]) > 1
                and component_by_id[edge.source_node_id] is component_by_id[edge.target_node_id]
            )
        ),
        key=lambda v: (v.source_node_id, v.target_node_id, v.edge_name),
    )
