# src/action_machine/model/graph_model/edges/required_context_graph_edge.py
"""
RequiredContextGraphEdge — COMPOSITION from RegularAspect → RequiredContext interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Typed alternative to composing a generic :class:`~graph.composition_graph_edge.CompositionGraphEdge`
with ``edge_name`` ``required_context`` and dot-path ``key`` in ``properties`` toward a
:class:`~action_machine.model.graph_model.required_context_graph_node.RequiredContextGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    RegularAspectGraphNode  ──required_context──►  RequiredContextGraphNode (``properties['key']``)
"""

from __future__ import annotations

from action_machine.model.graph_model.required_context_graph_node import RequiredContextGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class RequiredContextGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge regular aspect → one ``@context_requires`` slot vertex.
    CONTRACT: ``edge_name`` literal ``required_context``; ``properties['key']`` from ``required_context_node.node_obj.context_key``; ``is_dag`` False; source vertex is identified by caller-provided ``source_node_id`` / ``source_node_type``.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node_id: str,
        source_node_type: str,
        required_context_node: RequiredContextGraphNode,
    ) -> None:
        super().__init__(
            edge_name="required_context",
            is_dag=False,
            source_node_id=source_node_id,
            source_node_type=source_node_type,
            source_node=None,
            target_node_id=required_context_node.node_id,
            target_node_type=required_context_node.node_type,
            target_node=required_context_node,
            properties={"key": required_context_node.node_obj.context_key},
        )
