# src/action_machine/graph_model/edges/result_graph_edge.py
"""
ResultGraphEdge — AGGREGATION from Action host → Result interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralize ``edge_name=\"result\"`` and aggregation semantics for edges whose target
is the declared result schema vertex. Resolves ``result`` type via
:meth:`~action_machine.intents.action_schema.action_schema_intent_resolver.ActionSchemaIntentResolver.resolve_result_type`
on ``action_cls``. Raises :exc:`~action_machine.exceptions.ResultGraphEdgeResolutionError`
when the result type cannot be resolved.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    action_cls  →  resolve_result_type  →  ResultGraphEdge  ──►  Result (stub target)
"""

from __future__ import annotations

from typing import Any, cast

from action_machine.exceptions import ResultGraphEdgeResolutionError
from action_machine.graph_model.nodes.result_graph_node import ResultGraphNode
from action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from action_machine.system_core import TypeIntrospection
from graph.aggregation_graph_edge import AggregationGraphEdge
from graph.base_graph_node import BaseGraphNode


class ResultGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge host Action → result schema vertex.
    CONTRACT: ``edge_name`` ``result``, ``is_dag`` False; result type from ``resolve_result_type(action_cls)``; stub ``target_node_type`` property returns ``ResultGraphNode.NODE_TYPE``.
    INVARIANTS: Frozen via ``AggregationGraphEdge``; ``target_node`` optional stub until hydrated.
    FAILURES: :exc:`~action_machine.exceptions.ResultGraphEdgeResolutionError` when ``resolve_result_type`` returns ``None``.
    AI-CORE-END
    """

    def __init__(
        self,
        action_cls: type,
        source_node: BaseGraphNode[Any],
        *,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        result_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
        if result_type is None:
            qn = TypeIntrospection.full_qualname(action_cls)
            raise ResultGraphEdgeResolutionError(qn)
        super().__init__(
            edge_name="generic:result",
            is_dag=False,
            source_node_id=TypeIntrospection.full_qualname(action_cls),
            source_node=source_node,
            target_node_id=TypeIntrospection.full_qualname(result_type),
            target_node=target_node,
        )

    @property
    def target_node_type(self) -> str:
        if self.target_node is not None:
            return cast(str, self.target_node.node_type)
        return ResultGraphNode.NODE_TYPE
