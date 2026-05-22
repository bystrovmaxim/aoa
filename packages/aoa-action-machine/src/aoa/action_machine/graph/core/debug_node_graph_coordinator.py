# packages/aoa-action-machine/src/aoa/action_machine/graph/core/debug_node_graph_coordinator.py
"""
DebugNodeGraphCoordinator — graph assembly that keeps forbidden DAG cycles for inspection.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Builds the same interchange graph as :class:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator`,
but does not reject directed cycles formed by edges marked ``is_dag=True``. Instead, it records
the offending DAG edges in :attr:`dag_cycle_violations` so visualizers can highlight them.

Do not use this as a production runtime default. :class:`~aoa.action_machine.runtime.action_product_machine.ActionProductMachine`
must call :meth:`assert_no_dag_cycle_violations` before action execution and fail when violations exist.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core._dag import DagCycleViolation, dag_cycle_violations_for
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator


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

    def _validate_dag_acyclicity(
        self,
        nodes: dict[str, BaseGraphNode[Any]],
        _dag_adjacency: dict[str, list[str]],
    ) -> None:
        """Collect forbidden DAG-cycle edges instead of rejecting the graph."""
        object.__setattr__(self, "_dag_cycle_violations", tuple(dag_cycle_violations_for(nodes)))
