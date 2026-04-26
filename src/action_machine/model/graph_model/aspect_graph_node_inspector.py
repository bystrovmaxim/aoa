# src/action_machine/model/graph_model/aspect_graph_node_inspector.py
"""
AspectGraphNodeInspector — minimal aspect-node inspector stub.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide the first explicit entry point for aspect-node inspection in the
node-graph model. The current implementation only validates the incoming type
reference and returns an empty list.
"""

from __future__ import annotations

from typing import Any

from action_machine.introspection_tools import CallableKind, IntentIntrospection
from action_machine.model.graph_model.regular_aspect_graph_node import (
    RegularAspectGraphNode,
)
from graph.base_graph_node import BaseGraphNode
from graph.validation import require_non_null


class AspectGraphNodeInspector:
    """Minimal inspector stub for regular-aspect graph nodes."""

    @staticmethod
    def inspect(target_type: type | None) -> list[BaseGraphNode[Any]]:
        """Return regular-aspect nodes for ``target_type`` in class declaration order."""
        target_type = require_non_null("target_type", target_type)
        regular_aspect_callables = IntentIntrospection.collect_own_class_callables_by_callable_kind(
            target_type,
            CallableKind.REGULAR_ASPECT,
        )
        regular_aspect_nodes: list[BaseGraphNode[Any]] = [
            RegularAspectGraphNode(aspect_callable)
            for aspect_callable in regular_aspect_callables
        ]
        return regular_aspect_nodes
