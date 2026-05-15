# packages/aoa-action-machine/src/aoa/action_machine/graph_model/nodes/entity_field_graph_node.py
"""
EntityFieldGraphNode — interchange node for one scalar field on a ``BaseEntity`` class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One vertex per non-relation model field, composed from the host
:class:`~aoa.action_machine.graph_model.nodes.entity_graph_node.EntityGraphNode` via
:class:`~aoa.action_machine.graph_model.edges.entity_field_graph_edge.EntityFieldGraphEdge`.
Relation slots from :meth:`~aoa.action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver.resolve_entity_relations`
do not get a row. Field order for consumers is only on that edge's ``properties.ordinal``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    EntityGraphNode  ──{entity_field}──►  EntityFieldGraphNode (scalar only)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar, get_args, get_origin

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.base_graph_node import BaseGraphNode


@dataclass(frozen=True)
class EntityFieldGraphPayload:
    """Frozen payload; ``primary_key_hint`` is heuristic (``field_name == "id"``), not schema authority."""

    entity_type: type[BaseEntity]
    field_name: str
    field_type: str
    primary_key_hint: bool


@dataclass(init=False, frozen=True)
class EntityFieldGraphNode(BaseGraphNode[EntityFieldGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for one scalar ``BaseEntity`` model field (non-relation).
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(entity_type) + ':' + field_name``; :attr:`NODE_TYPE` ``EntityField``; :meth:`to_dict` exposes ``field_type`` and ``primary_key_hint`` only (no ``ordinal`` on the node).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "EntityField"

    @classmethod
    def pretty_annotation(cls, annotation: Any) -> str:
        """
        Return a stable display string for a Python type annotation (unwraps ``Annotated``).

        AI-CORE-BEGIN
        ROLE: Serialize annotations for interchange ``field_type`` strings on entity field vertices.
        CONTRACT: Unwraps ``typing.Annotated`` to the inner type; uses ``__qualname__`` for simple types.
        AI-CORE-END
        """
        ann = annotation
        while get_origin(ann) is Annotated:
            args = get_args(ann)
            if not args:
                break
            ann = args[0]
        origin = get_origin(ann)
        if origin is None:
            return ann.__qualname__ if isinstance(ann, type) else str(ann)
        rendered_args = ", ".join(cls.pretty_annotation(arg) for arg in get_args(ann))
        name = getattr(origin, "__qualname__", str(origin))
        return f"{name}[{rendered_args}]" if rendered_args else name

    def __init__(self, entity_cls: type[BaseEntity], field_name: str, *, annotation: Any) -> None:
        if not isinstance(entity_cls, type) or not issubclass(entity_cls, BaseEntity):
            msg = f"entity_cls must be a BaseEntity subclass, got {entity_cls!r}"
            raise TypeError(msg)

        stripped = field_name.strip()
        field_type = type(self).pretty_annotation(annotation)
        primary_key_hint = stripped == "id"
        node_obj = EntityFieldGraphPayload(
            entity_type=entity_cls,
            field_name=stripped,
            field_type=field_type,
            primary_key_hint=primary_key_hint,
        )
        super().__init__(
            node_id=f"{TypeIntrospection.full_qualname(entity_cls)}:{stripped}",
            node_type=EntityFieldGraphNode.NODE_TYPE,
            label=stripped,
            properties={
                "field_type": field_type,
                "primary_key_hint": primary_key_hint,
            },
            node_obj=node_obj,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "properties": {
                "field_type": str(self.properties["field_type"]),
                "primary_key_hint": bool(self.properties["primary_key_hint"]),
            },
        }

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Scalar field rows only ship outbound edges when future metadata requires them."""
        return []

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Companion expansion is driven from the owning ``EntityGraphNode``."""
        return []
