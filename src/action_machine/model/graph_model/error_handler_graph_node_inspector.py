# src/action_machine/model/graph_model/error_handler_graph_node_inspector.py
"""
ErrorHandlerGraphNodeInspector — minimal error-handler node inspector.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide an explicit entry point for error-handler node inspection in the
node-graph model.
"""

from __future__ import annotations

from typing import Any

from action_machine.introspection_tools import CallableKind, IntentIntrospection
from action_machine.model.graph_model.error_handler_graph_node import (
    ErrorHandlerGraphNode,
)
from graph.base_graph_node import BaseGraphNode
from graph.validation import require_non_null


class ErrorHandlerGraphNodeInspector:
    """Minimal inspector for error-handler graph nodes."""

    @staticmethod
    def inspect(target_type: type | None) -> list[BaseGraphNode[Any]]:
        """Return error-handler nodes for ``target_type`` in class declaration order."""
        target_type = require_non_null("target_type", target_type)
        error_handler_callables = IntentIntrospection.collect_own_class_callables_by_callable_kind(
            target_type,
            CallableKind.ON_ERROR,
        )
        error_handler_nodes: list[BaseGraphNode[Any]] = [
            ErrorHandlerGraphNode(handler_callable)
            for handler_callable in error_handler_callables
        ]
        return error_handler_nodes
