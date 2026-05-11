# packages/aoa-action-machine/src/aoa/action_machine/graph_model/edges/entity_schema_graph_edge.py
"""
EntitySchemaGraphEdge — AGGREGATION from field/property node → declared entity class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When a schema field or property uses ``BaseEntity.schema(...)`` (``Annotated`` +
:class:`~aoa.action_machine.domain.entity_schema_marker.EntitySchemaMarker`), the
interchange graph records a semantic link from that concrete field/property node
to the host entity class. The wire payload remains JSON Schema on the field row;
this edge is only the entity binding for coordinators and tooling.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    FieldGraphNode / PropertyFieldGraphNode
              |
              +-- entity_schema -->> EntityGraphNode (``node_id`` = entity qualname)
"""

from __future__ import annotations

import types
import typing
from typing import Any, get_args, get_origin

from aoa.action_machine.domain.entity_schema_marker import entity_schema_marker_from_annotated
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.aggregation_graph_edge import AggregationGraphEdge


def _unwrap_optional(annotation: Any) -> Any:
    """Return ``X`` from ``Optional[X]`` / ``X | None``, or ``annotation`` unchanged."""
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def entity_schema_projection_target_from_annotation(annotation: Any) -> type | None:
    """Return entity class from a ``BaseEntity.schema(...)`` annotation, if present."""
    actual_type = _unwrap_optional(annotation)
    marker = entity_schema_marker_from_annotated(actual_type)
    return None if marker is None else marker.entity_cls


class EntitySchemaGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge ``field/property → entity class`` for ``BaseEntity.schema(...)`` annotations.
    CONTRACT: ``edge_name`` ``entity_schema``; ``is_dag`` True; ``target_node_id`` is entity full qualname; ``properties`` are JSON-only.
    INVARIANTS: Frozen via ``AggregationGraphEdge``; ``target_node`` wired by coordinator when entity node exists.
    AI-CORE-END
    """

    def __init__(self, *, entity_cls: type) -> None:
        super().__init__(
            edge_name="entity_schema",
            is_dag=True,
            target_node_id=TypeIntrospection.full_qualname(entity_cls),
            target_node=None,
            properties={},
        )
