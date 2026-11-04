# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_schema_graph_edge.py
"""
EntitySchemaGraphEdge — AGGREGATION from field/property node → declared entity class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When a schema field or property is typed by an entity — a projection
``BaseEntity.schema(...)`` (``Annotated`` +
:class:`~aoa.action_machine.domain.entity_schema_marker.EntitySchemaMarker`), or the
entity class itself, bare, ``| None`` or ``list[...]`` — the interchange graph
records a semantic link from that concrete field/property node to the entity class. The wire payload remains JSON Schema on the field row;
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
from aoa.action_machine.graph.core.aggregation_graph_edge import AggregationGraphEdge
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


def _unwrap_optional(annotation: Any) -> Any:
    """Return ``X`` from ``Optional[X]`` / ``X | None``, or ``annotation`` unchanged."""
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        args = [a for a in get_args(annotation) if a is not types.NoneType]
        if len(args) == 1:
            return args[0]
    return annotation


def _is_declared_entity(candidate: Any) -> bool:
    """
    True for a class declared with ``@entity`` — the classes the graph has entity nodes for.

    Read from the attribute the decorator sets, so this module imports nothing of the domain
    layer, which itself imports the graph.
    """
    return isinstance(candidate, type) and getattr(candidate, "_entity_info", None) is not None


def entity_schema_target_from_annotation(annotation: Any) -> type | None:
    """
    Return the entity a field is typed by: a projection's entity, or an entity class itself.

    ``X | None`` and ``list[X]`` are looked through, so a field typed ``Entity``, ``Entity | None`` or
    ``list[Entity]`` is linked to ``Entity`` as a projection ``Entity.schema(...)`` is.
    """
    actual_type = _unwrap_optional(annotation)
    marker = entity_schema_marker_from_annotated(actual_type)
    if marker is not None:
        return marker.entity_cls
    if get_origin(actual_type) in (list, tuple):
        arguments = [argument for argument in get_args(actual_type) if argument is not Ellipsis]
        actual_type = _unwrap_optional(arguments[0]) if len(arguments) == 1 else None
    if _is_declared_entity(actual_type):
        return actual_type
    return None


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

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }
