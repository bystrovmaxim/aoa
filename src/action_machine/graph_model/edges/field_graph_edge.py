# src/action_machine/graph_model/edges/field_graph_edge.py
"""
FieldGraphEdge — COMPOSITION from Params / Result → Field interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror params / result schema field companions: composition with ``edge_name`` ``field``
from an interchange vertex to a :class:`~action_machine.graph_model.nodes.field_graph_node.FieldGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Params / Result (source id + type)  ──{field}──►  FieldGraphNode
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from action_machine.graph_model.nodes.field_graph_node import FieldGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class FieldGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge schema host (params or result) → declared field vertex.
    CONTRACT: ``edge_name`` literal ``field``; ``is_dag`` False; ``source_node`` / ``target_node`` wired when emitted.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        field_node: FieldGraphNode,
        source_node: BaseGraphNode[Any],
    ) -> None:
        super().__init__(
            edge_name="field",
            is_dag=False,
            source_node_id=source_node.node_id,
            source_node=source_node,
            target_node_id=field_node.node_id,
            target_node=field_node,
        )

    @classmethod
    def get_field_edges(cls, schema_cls: type, source_host: BaseGraphNode[Any]) -> list[FieldGraphEdge]:
        """Build composition edges from params or result host to declared Pydantic field nodes."""
        fields = cls._field_graph_nodes_for_host(schema_cls)
        return [cls(field_node=fd, source_node=source_host) for fd in fields]

    @classmethod
    def _field_graph_nodes_for_host(cls, host_cls: type) -> list[FieldGraphNode]:
        """One ``FieldGraphNode`` per ``host_cls.model_fields`` entry (empty when none)."""
        model_fields = getattr(host_cls, "model_fields", None)
        if not isinstance(model_fields, Mapping):
            return []
        out: list[FieldGraphNode] = []
        for field_name, finfo in model_fields.items():
            out.append(
                FieldGraphNode(
                    host_cls,
                    field_name,
                    description=finfo.description,
                    required=bool(finfo.is_required()),
                ),
            )
        return out
