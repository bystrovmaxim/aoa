# src/action_machine/model/graph_model/edges/error_handler_graph_edge.py
"""
ErrorHandlerGraphEdge — COMPOSITION from Action → ErrorHandler interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~action_machine.model.graph_model.action_graph_node.ActionGraphNode.get_error_handler_edges`:
composition keyed by handler node's ``label``, ``is_dag=False``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──{handler_label}──►  ErrorHandlerGraphNode
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.on_error.on_error_intent_resolver import (
    OnErrorIntentResolver,
)
from action_machine.model.base_action import BaseAction
from action_machine.model.graph_model.error_handler_graph_node import ErrorHandlerGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class ErrorHandlerGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge host Action → ``@on_error`` handler vertex.
    CONTRACT: ``edge_name`` equals ``handler_node.label``; ``target_node`` is the ``ErrorHandlerGraphNode`` instance.
    INVARIANTS: Frozen via ``CompositionGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node: BaseGraphNode[Any],
        handler_node: ErrorHandlerGraphNode,
    ) -> None:
        super().__init__(
            edge_name=handler_node.label,
            is_dag=False,
            source_node_id=source_node.node_id,
            source_node_type=source_node.node_type,
            source_node=source_node,
            target_node_id=handler_node.node_id,
            target_node_type=handler_node.node_type,
            target_node=handler_node,
        )

    @staticmethod
    def edges_from_error_handlers(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[ErrorHandlerGraphEdge]:
        """Return error handler composition edges for ``action_cls``."""
        return [
            ErrorHandlerGraphEdge(
                source_node=source_node,
                handler_node=ErrorHandlerGraphNode(error_handler_callable, action_cls),
            )
            for error_handler_callable in OnErrorIntentResolver.resolve_error_handlers(action_cls)
        ]
