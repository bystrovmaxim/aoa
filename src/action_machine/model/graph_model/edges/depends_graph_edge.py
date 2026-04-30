# src/action_machine/model/graph_model/edges/depends_graph_edge.py
"""
DependsGraphEdge — ASSOCIATION for ``@depends`` from Action → declared dependency type.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~action_machine.model.graph_model.action_graph_node.ActionGraphNode._get_depends_edges`:
``edge_name`` ``@depends``, ``is_dag=True``, ``target_node`` stub until hydrated.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@depends──►  Action | Resource | … (interchange id + type)
"""

from __future__ import annotations

from typing import Any

from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode


class DependsGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge for ``@depends`` slots on an Action host.
    CONTRACT: ``edge_name`` ``@depends``, ``is_dag`` True; ``target_node_type`` set by caller per resolved dependency class.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node_id: str,
        source_node_type: str,
        source_node: BaseGraphNode[Any],
        target_node_id: str,
        target_node_type: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="@depends",
            is_dag=True,
            source_node_id=source_node_id,
            source_node_type=source_node_type,
            source_node=source_node,
            target_node_id=target_node_id,
            target_node_type=target_node_type,
            target_node=target_node,
        )
