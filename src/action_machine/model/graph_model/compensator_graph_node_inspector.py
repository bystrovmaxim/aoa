# src/action_machine/model/graph_model/compensator_graph_node_inspector.py
"""
CompensatorGraphNodeInspector — minimal compensator node inspector.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide an explicit entry point for compensator node inspection in the
node-graph model.
"""

from __future__ import annotations

from typing import Any

from action_machine.introspection_tools import CallableKind, IntentIntrospection
from action_machine.model.graph_model.compensator_graph_node import (
    CompensatorGraphNode,
)
from graph.base_graph_node import BaseGraphNode
from graph.validation import require_non_null


class CompensatorGraphNodeInspector:
    """Minimal inspector for compensator graph nodes."""

    @staticmethod
    def inspect(target_type: type | None) -> list[BaseGraphNode[Any]]:
        """Return compensator nodes for ``target_type`` in class declaration order."""
        target_type = require_non_null("target_type", target_type)
        compensator_callables = IntentIntrospection.collect_own_class_callables_by_callable_kind(
            target_type,
            CallableKind.COMPENSATE,
        )
        compensator_nodes: list[BaseGraphNode[Any]] = [
            CompensatorGraphNode(compensator_callable)
            for compensator_callable in compensator_callables
        ]
        return compensator_nodes
