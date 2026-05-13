# packages/aoa-action-machine/src/aoa/action_machine/graph_model/edges/field_graph_edge.py
"""
FieldGraphEdge — COMPOSITION from Params / Result → Field interchange graph node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror params / result schema field companions: composition with ``edge_name`` ``field``
from an interchange graph node to a :class:`~aoa.action_machine.graph_model.nodes.field_graph_node.FieldGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Params / Result (source id + type)  ──{field}──►  FieldGraphNode
"""

from __future__ import annotations

import types
import typing
from collections.abc import Mapping
from typing import Any, get_args, get_origin, get_type_hints

from aoa.action_machine.graph_model.edges.entity_schema_graph_edge import (
    entity_schema_projection_target_from_annotation,
)
from aoa.action_machine.graph_model.nodes.field_graph_node import FieldGraphNode
from aoa.action_machine.model.json_schema_value import get_json_schema_value_metadata
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.composition_graph_edge import CompositionGraphEdge


def _unwrap_optional(annotation: Any) -> Any:
    """Return ``X`` from ``Optional[X]`` / ``X | None``, or ``annotation`` unchanged."""
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


class FieldGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge schema host (params or result) → declared field graph node.
    CONTRACT: ``edge_name`` literal ``field``; ``is_dag`` False; ``target_node`` wired when emitted.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        field_node: FieldGraphNode,
    ) -> None:
        super().__init__(
            edge_name="field",
            is_dag=False,
            target_node_id=field_node.node_id,
            target_node=field_node,
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }

    @classmethod
    def get_field_edges(cls, schema_cls: type, _source_host: BaseGraphNode[Any]) -> list[FieldGraphEdge]:
        """Build composition edges from params or result host to declared Pydantic field nodes."""
        fields = cls._field_graph_nodes_for_host(schema_cls)
        return [cls(field_node=fd) for fd in fields]

    @classmethod
    def _field_graph_nodes_for_host(cls, host_cls: type) -> list[FieldGraphNode]:
        """One ``FieldGraphNode`` per ``host_cls.model_fields`` entry (empty when none)."""
        model_fields = getattr(host_cls, "model_fields", None)
        if not isinstance(model_fields, Mapping):
            return []
        try:
            hints = get_type_hints(host_cls, include_extras=True)
        except Exception:
            hints = {}
        out: list[FieldGraphNode] = []
        for field_name, finfo in model_fields.items():
            annotation = hints.get(field_name, finfo.annotation)
            actual_type = _unwrap_optional(annotation)
            jsv_meta = get_json_schema_value_metadata(actual_type)
            entity_schema_target = entity_schema_projection_target_from_annotation(annotation)
            out.append(
                FieldGraphNode(
                    host_cls,
                    field_name,
                    description=finfo.description,
                    required=bool(finfo.is_required()),
                    json_schema_value=jsv_meta is not None,
                    json_schema_name=jsv_meta["name"] if jsv_meta else None,
                    json_schema=jsv_meta["schema"] if jsv_meta else None,
                    entity_schema_target=entity_schema_target,
                ),
            )
        return out
