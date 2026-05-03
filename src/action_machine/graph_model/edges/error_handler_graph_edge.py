# src/action_machine/graph_model/edges/error_handler_graph_edge.py
"""
ErrorHandlerGraphEdge — COMPOSITION from Action → ErrorHandler interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~action_machine.graph_model.edges.error_handler_graph_edge.ErrorHandlerGraphEdge.get_on_error_handlers_edges`:
composition keyed by handler node's ``label``, ``is_dag=False``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──{handler_label}──►  ErrorHandlerGraphNode
"""

from __future__ import annotations

from typing import Any

from action_machine.graph_model.nodes.error_handler_graph_node import ErrorHandlerGraphNode
from action_machine.intents.on_error.on_error_intent_resolver import OnErrorIntentResolver
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
        handler_node: ErrorHandlerGraphNode,
    ) -> None:
        super().__init__(
            edge_name="@on_error",
            is_dag=False,
            target_node_id=handler_node.node_id,
            target_node=handler_node,
        )

    @staticmethod
    def get_on_error_handlers_edges(
        action_cls: type[Any],
    ) -> list[ErrorHandlerGraphEdge]:
        """Return error handler composition edges for ``action_cls``."""
        return [
            ErrorHandlerGraphEdge(
                handler_node=ErrorHandlerGraphNode(error_handler_callable, action_cls),
            )
            for error_handler_callable in OnErrorIntentResolver.resolve_error_handlers(action_cls)
        ]
