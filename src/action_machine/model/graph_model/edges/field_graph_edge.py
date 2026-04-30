# src/action_machine/model/graph_model/edges/field_graph_edge.py
"""
FieldGraphEdge — COMPOSITION from Params → Field interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror params-schema field companions: composition with ``edge_name`` ``field:{name}``
from a params interchange vertex to a :class:`~action_machine.model.graph_model.field_graph_node.FieldGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Params (source id + type)  ──{field:`name`}──►  FieldGraphNode
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from action_machine.model.graph_model.field_graph_node import FieldGraphNode

if TYPE_CHECKING:
    from action_machine.model.base_params import BaseParams
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class FieldGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge Params host → declared field vertex.
    CONTRACT: ``edge_name`` ``field:`` + stripped field name (``_`` when empty); ``is_dag`` False; ``target_node`` is the ``FieldGraphNode``.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    @staticmethod
    def for_params(
        params_cls: type[BaseParams],
        params_node_id: str,
    ) -> list[FieldGraphEdge]:
        """Build composition edges from params node to declared Pydantic field nodes."""
        from action_machine.model.graph_model.params_graph_node import ParamsGraphNode

        fields = ParamsGraphNode._field_graph_nodes_for_params(params_cls)
        return [
            FieldGraphEdge(
                params_node_id=params_node_id,
                params_node_type=ParamsGraphNode.NODE_TYPE,
                field_node=fd,
            )
            for fd in fields
        ]

    def __init__(
        self,
        *,
        params_node_id: str,
        params_node_type: str,
        field_node: FieldGraphNode,
        source_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="field",
            is_dag=False,
            source_node_id=params_node_id,
            source_node_type=params_node_type,
            source_node=source_node,
            target_node_id=field_node.node_id,
            target_node_type=field_node.node_type,
            target_node=field_node,
        )
