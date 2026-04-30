# src/action_machine/model/graph_model/edges/checker_graph_edge.py
"""
CheckerGraphEdge — COMPOSITION from RegularAspect → Checker interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides the typed :class:`CheckerGraphEdge` for each :class:`~action_machine.model.graph_model.checker_graph_node.CheckerGraphNode`
under a :class:`~action_machine.model.graph_model.regular_aspect_graph_node.RegularAspectGraphNode`
(``edge_name`` ``@result_checker``, ``is_dag`` False), instead of synthesizing a bare
:class:`~graph.composition_graph_edge.CompositionGraphEdge`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    RegularAspectGraphNode  ──@result_checker──►  CheckerGraphNode
"""

from __future__ import annotations

from action_machine.model.graph_model.checker_graph_node import CheckerGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class CheckerGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge regular aspect vertex → checker row.
    CONTRACT: ``edge_name`` literal ``@result_checker``; ``is_dag`` False; ``source_node`` left unset (``None``) so frozen edge equality does not recurse through the host :class:`~action_machine.model.graph_model.regular_aspect_graph_node.RegularAspectGraphNode`; ``target_node`` is the checker vertex.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        checker_node: CheckerGraphNode,
        source_node_id: str,
        source_node_type: str,
    ) -> None:
        super().__init__(
            edge_name="@result_checker",
            is_dag=False,
            source_node_id=source_node_id,
            source_node_type=source_node_type,
            source_node=None,
            target_node_id=checker_node.node_id,
            target_node_type=checker_node.node_type,
            target_node=checker_node,
        )
