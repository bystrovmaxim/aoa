# src/action_machine/graph_model/edges/params_graph_edge.py
"""
ParamsGraphEdge — AGGREGATION from Action host → Params interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralize ``edge_name=\"params\"`` and aggregation semantics for edges whose target
is the declared params schema vertex. Resolves ``params`` type via
:meth:`~action_machine.intents.action_schema.action_schema_intent_resolver.ActionSchemaIntentResolver.resolve_params_type`
on ``action_cls``. Raises :exc:`~action_machine.exceptions.ParamsGraphEdgeResolutionError`
when that resolver returns ``None``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    action_cls  →  resolve_params_type  →  ParamsGraphEdge  ──►  Params (stub target)
"""

from __future__ import annotations

from typing import Any

from action_machine.exceptions.params_graph_edge_resolution_error import ParamsGraphEdgeResolutionError
from action_machine.intents.action_schema.action_schema_intent_resolver import ActionSchemaIntentResolver
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.aggregation_graph_edge import AggregationGraphEdge
from graph.base_graph_node import BaseGraphNode


class ParamsGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge host Action → params schema vertex.
    CONTRACT: ``edge_name`` ``params``, ``is_dag`` False; params type from ``resolve_params_type(action_cls)``. ``target_node`` may be wired by the interchange coordinator.
    INVARIANTS: Frozen via ``AggregationGraphEdge``; ``target_node`` optional stub until hydrated.
    FAILURES: :exc:`~action_machine.exceptions.ParamsGraphEdgeResolutionError` when ``resolve_params_type`` returns ``None``.
    AI-CORE-END
    """

    def __init__(
        self,
        action_cls: type,
        *,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        params_type = ActionSchemaIntentResolver.resolve_params_type(action_cls)
        if params_type is None:
            qn = TypeIntrospection.full_qualname(action_cls)
            raise ParamsGraphEdgeResolutionError(qn)

        super().__init__(
            edge_name="generic:params",
            is_dag=False,
            target_node_id=TypeIntrospection.full_qualname(params_type),
            target_node=target_node,
        )
