# src/action_machine/model/graph_model/edges/field_graph_edge.py
"""
FieldGraphEdge — COMPOSITION from Params / Result → Field interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror params / result schema field companions: composition with ``edge_name`` ``field``
from an interchange vertex to a :class:`~action_machine.model.graph_model.field_graph_node.FieldGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Params / Result (source id + type)  ──{field}──►  FieldGraphNode
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from action_machine.model.graph_model.field_graph_node import FieldGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class FieldGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge schema host (params or result) → declared field vertex.
    CONTRACT: ``edge_name`` literal ``field``; ``is_dag`` False; ``target_node`` is the ``FieldGraphNode``.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        node_id: str,
        node_type: str,
        field_node: FieldGraphNode,
        source_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="field",
            is_dag=False,
            source_node_id=node_id,
            source_node_type=node_type,
            source_node=source_node,
            target_node_id=field_node.node_id,
            target_node_type=field_node.node_type,
            target_node=field_node,
        )

    @classmethod
    def for_params(
        cls,
        cls_type: type,
        node_id: str,
        node_type: str,
    ) -> list[FieldGraphEdge]:
        """Build composition edges from params node to declared Pydantic field nodes."""

        fields = cls._field_graph_nodes_for_host(cls_type)
        return [
            cls(
                node_id=node_id,
                node_type=node_type,
                field_node=fd,
            )
            for fd in fields
        ]

    @classmethod
    def for_result(
        cls,
        cls_type: type,
        node_id: str,
        node_type: str,
    ) -> list[FieldGraphEdge]:
        """Build composition edges from result node to declared Pydantic field nodes."""

        fields = cls._field_graph_nodes_for_host(cls_type)
        return [
            cls(
                node_id=node_id,
                node_type=node_type,
                field_node=fd,
            )
            for fd in fields
        ]

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
