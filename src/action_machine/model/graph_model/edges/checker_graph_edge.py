# src/action_machine/model/graph_model/edges/checker_graph_edge.py
"""
CheckerGraphEdge — COMPOSITION from RegularAspect → Checker interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Typed alternative to constructing a raw :class:`~graph.composition_graph_edge.CompositionGraphEdge`
from a regular aspect host to its :class:`~action_machine.model.graph_model.checker_graph_node.CheckerGraphNode`
companions (``edge_name`` ``checker:{field}``, ``is_dag`` False).

This module stays opt-in until wiring replaces generic composition edges on
:class:`~action_machine.model.graph_model.regular_aspect_graph_node.RegularAspectGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    RegularAspectGraphNode  ──checker:{field}──►  CheckerGraphNode
"""

from __future__ import annotations

from action_machine.model.graph_model.checker_graph_node import CheckerGraphNode
from action_machine.model.graph_model.regular_aspect_graph_node import RegularAspectGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class CheckerGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge regular aspect vertex → checker row.
    CONTRACT: ``edge_name`` ``checker:{field}`` from ``checker_node.node_obj.field_name`` (fallback ``_``); ``is_dag`` False; ``source_node`` / ``target_node`` materialized when passed.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        aspect_node: RegularAspectGraphNode,
        checker_node: CheckerGraphNode,
    ) -> None:
        field = checker_node.node_obj.field_name.strip() or "_"
        super().__init__(
            edge_name=f"checker:{field}",
            is_dag=False,
            source_node_id=aspect_node.node_id,
            source_node_type=aspect_node.node_type,
            source_node=aspect_node,
            target_node_id=checker_node.node_id,
            target_node_type=checker_node.node_type,
            target_node=checker_node,
        )
