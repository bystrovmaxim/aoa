# packages/aoa-graph/src/aoa/graph/debug_node_graph_coordinator.py
"""
DebugNodeGraphCoordinator — graph assembly that keeps forbidden DAG cycles for inspection.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Builds the same interchange graph as :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator`,
but does not reject directed cycles formed by edges marked ``is_dag=True``. Instead, it records
the offending DAG edges in :attr:`dag_cycle_violations` so visualizers can highlight them.

Do not use this as a production runtime default. :class:`~aoa.action_machine.runtime.action_product_machine.ActionProductMachine`
must call :meth:`assert_no_dag_cycle_violations` before action execution and fail when violations exist.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import rustworkx as rx

from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.exceptions import InvalidGraphError
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator


@dataclass(frozen=True)
class DagCycleViolation:
    """
    AI-CORE-BEGIN
    ROLE: Debug metadata for one ``is_dag=True`` edge that participates in a forbidden directed cycle.
    CONTRACT: ``source_node_id`` and ``target_node_id`` are materialized interchange ids; ``edge_name`` is the edge slot.
    AI-CORE-END
    """

    source_node_id: str
    target_node_id: str
    edge_name: str


class DebugNodeGraphCoordinator(NodeGraphCoordinator):
    """
    AI-CORE-BEGIN
    ROLE: Debug-only coordinator that builds even when ``is_dag=True`` edges form directed cycles.
    CONTRACT: Same public graph accessors as :class:`NodeGraphCoordinator`; :attr:`dag_cycle_violations` lists offending DAG edges; :meth:`assert_no_dag_cycle_violations` is the runtime guard.
    INVARIANTS: Duplicate ids and missing targets still raise during build; only DAG-cycle rejection is relaxed for inspection.
    AI-CORE-END
    """

    __slots__ = ("_dag_cycle_violations",)

    def __init__(self) -> None:
        super().__init__()
        self._dag_cycle_violations: tuple[DagCycleViolation, ...] = ()

    @property
    def dag_cycle_violations(self) -> tuple[DagCycleViolation, ...]:
        """Forbidden ``is_dag=True`` cycle edges collected during debug graph build."""
        return self._dag_cycle_violations

    @property
    def has_dag_cycle_violations(self) -> bool:
        """Whether this debug-built graph contains forbidden DAG-cycle edges."""
        return bool(self._dag_cycle_violations)

    def assert_no_dag_cycle_violations(self) -> None:
        """Fail before action execution if the debug graph contains forbidden DAG cycles."""
        if not self._dag_cycle_violations:
            return
        sample = ", ".join(
            f"{v.source_node_id} -[{v.edge_name}]-> {v.target_node_id}"
            for v in self._dag_cycle_violations[:3]
        )
        suffix = "" if len(self._dag_cycle_violations) <= 3 else f" (+{len(self._dag_cycle_violations) - 3} more)"
        raise InvalidGraphError(
            "Debug graph contains forbidden cycles among edges with is_dag=True; "
            "action execution is disabled. "
            f"Examples: {sample}{suffix}.",
        )

    def _validate_dag_acyclicity(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        """Collect forbidden DAG-cycle edges instead of rejecting the graph."""
        object.__setattr__(self, "_dag_cycle_violations", tuple(_dag_cycle_violations_for(nodes)))


def _dag_cycle_violations_for(nodes: dict[str, BaseGraphNode[Any]]) -> list[DagCycleViolation]:
    ids = sorted(nodes.keys())
    if not ids:
        return []
    g = rx.PyDiGraph()
    idx = {nid: g.add_node(nid) for nid in ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in ids}
    dag_edges: list[DagCycleViolation] = []
    for source_id, node in nodes.items():
        for edge in node.get_all_edges():
            if not edge.is_dag:
                continue
            adjacency[source_id].append(edge.target_node_id)
            dag_edges.append(DagCycleViolation(source_id, edge.target_node_id, edge.edge_name))
            g.add_edge(idx[source_id], idx[edge.target_node_id], edge.edge_name)
    if not dag_edges or rx.is_directed_acyclic_graph(g):
        return []

    components = _strongly_connected_components(ids, adjacency)
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


def _strongly_connected_components(
    ids: Sequence[str],
    adjacency: dict[str, list[str]],
) -> list[frozenset[str]]:
    """Tarjan SCC over the DAG-edge slice; keeps diagnostics independent of rustworkx internals."""
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
