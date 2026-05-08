# src/action_machine/graph_model/edges/result_graph_edge.py
"""
ResultGraphEdge — AGGREGATION from Action host → Result interchange graph node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralize ``edge_name=\"result\"`` and aggregation semantics for edges whose target
is the declared result schema graph node. Resolves ``result`` type via
:meth:`~action_machine.intents.action_schema.action_schema_intent_resolver.ActionSchemaIntentResolver.resolve_result_type`
on ``action_cls``. Raises :exc:`~action_machine.exceptions.ResultGraphEdgeResolutionError`
when the result type cannot be resolved.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    action_cls  →  resolve_result_type  →  ResultGraphEdge  ──►  Result (stub target)
"""

from __future__ import annotations

from typing import Any

from action_machine.exceptions.result_graph_edge_resolution_error import ResultGraphEdgeResolutionError
from action_machine.intents.action_schema.action_schema_intent_resolver import ActionSchemaIntentResolver
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.aggregation_graph_edge import AggregationGraphEdge
from graph.base_graph_node import BaseGraphNode


class ResultGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge host Action → result schema graph node.
    CONTRACT: ``edge_name`` ``result``, ``is_dag`` False; ``target_node`` may be wired by the interchange coordinator.
    INVARIANTS: Frozen via ``AggregationGraphEdge``; ``target_node`` optional stub until hydrated.
    FAILURES: :exc:`~action_machine.exceptions.ResultGraphEdgeResolutionError` when ``resolve_result_type`` raises :exc:`ValueError` (missing or invalid ``BaseResult`` binding).
    AI-CORE-END
    """

    def __init__(
        self,
        action_cls: type,
        *,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        try:
            result_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
        except ValueError as exc:
            raise ResultGraphEdgeResolutionError(TypeIntrospection.full_qualname(action_cls)) from exc

        super().__init__(
            edge_name="generic:result",
            is_dag=False,
            target_node_id=TypeIntrospection.full_qualname(result_type),
            target_node=target_node,
        )
