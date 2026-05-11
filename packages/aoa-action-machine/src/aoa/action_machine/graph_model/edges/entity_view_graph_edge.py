# packages/aoa-action-machine/src/aoa/action_machine/graph_model/edges/entity_view_graph_edge.py
"""
EntityViewGraphEdge — AGGREGATION from Params/Result host → declared entity class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When a schema field uses ``BaseEntity.schema(...)`` (``Annotated`` +
:class:`~aoa.action_machine.domain.entity_schema_marker.EntitySchemaMarker`), the
interchange graph records a semantic link from that field to the host entity
class. The wire payload remains JSON Schema on the field row; this edge is only
the entity binding for coordinators and tooling.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ResultGraphNode / ParamsGraphNode
              |
              +-- entity_view[field] -->> EntityGraphNode (``node_id`` = entity qualname)
"""

from __future__ import annotations

import types
import typing
from collections.abc import Iterator, Mapping
from typing import Any, get_args, get_origin, get_type_hints

from aoa.action_machine.domain.entity_schema_marker import entity_schema_marker_from_annotated
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.aggregation_graph_edge import AggregationGraphEdge
from aoa.graph.base_graph_node import BaseGraphNode


def _unwrap_optional(annotation: Any) -> Any:
    """Return ``X`` from ``Optional[X]`` / ``X | None``, or ``annotation`` unchanged."""
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def iter_entity_projection_field_targets(host_cls: type) -> Iterator[tuple[str, type]]:
    """
    Yield ``(field_name, entity_cls)`` for Pydantic fields whose annotation carries
    :class:`~aoa.action_machine.domain.entity_schema_marker.EntitySchemaMarker`.

    Uses ``get_type_hints(..., include_extras=True)`` so ``Annotated`` metadata is visible.
    """
    model_fields = getattr(host_cls, "model_fields", None)
    if not isinstance(model_fields, Mapping):
        return
    try:
        hints = get_type_hints(host_cls, include_extras=True)
    except Exception:
        hints = {}
    for field_name, finfo in model_fields.items():
        annotation = hints.get(field_name, finfo.annotation)
        actual_type = _unwrap_optional(annotation)
        marker = entity_schema_marker_from_annotated(actual_type)
        if marker is None:
            continue
        yield field_name, marker.entity_cls


class EntityViewGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge ``schema host → entity class`` for ``BaseEntity.schema(...)`` fields.
    CONTRACT: ``edge_name`` ``entity_view``; ``is_dag`` True; ``target_node_id`` is entity full qualname; ``properties`` JSON-only with at least ``field_name``.
    INVARIANTS: Frozen via ``AggregationGraphEdge``; ``target_node`` wired by coordinator when entity node exists.
    AI-CORE-END
    """

    def __init__(self, *, field_name: str, entity_cls: type) -> None:
        super().__init__(
            edge_name="entity_view",
            is_dag=True,
            target_node_id=TypeIntrospection.full_qualname(entity_cls),
            target_node=None,
            properties={"field_name": field_name},
        )

    @classmethod
    def get_entity_view_edges(
        cls,
        schema_cls: type,
        _source_host: BaseGraphNode[Any],
    ) -> list[EntityViewGraphEdge]:
        """Build one ``entity_view`` edge per entity-projection field on ``schema_cls``."""
        return [
            cls(field_name=field_name, entity_cls=entity_cls)
            for field_name, entity_cls in iter_entity_projection_field_targets(schema_cls)
        ]
