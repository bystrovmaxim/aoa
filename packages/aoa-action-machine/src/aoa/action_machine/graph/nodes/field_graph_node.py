# packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/field_graph_node.py
"""
FieldGraphNode — interchange node for one field under a host type (``parent_type``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode` for one logical field under a
caller-supplied host ``parent_type`` (typically a params or result schema class). ``node_id`` is the host
dotted id plus ``:`` plus the field name (``parent_type`` is only an argument to ``__init__``, not stored on the payload); ``node_obj`` is a frozen :class:`FieldGraphPayload`.

Constructor inputs mirror :class:`CheckerGraphNode`: ``parent_type``, ``field_name``, optional ``description``, ``required``, and optional JSON-schema metadata. Declared-field graphs are usually built via :class:`~aoa.action_machine.graph.edges.field_graph_edge.FieldGraphEdge`, which reads Pydantic ``model_fields`` / ``get_type_hints`` and attaches :class:`~aoa.action_machine.model.json_schema_value.JsonSchemaValue` metadata when applicable. Fields annotated with ``BaseEntity.schema(...)`` carry an outgoing ``entity_schema`` edge from the concrete field node to the entity node.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, ClassVar

from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.entity_schema_graph_edge import EntitySchemaGraphEdge
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


@dataclass(frozen=True)
class FieldGraphPayload:
    """Frozen payload for :attr:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode.node_obj` (field row metadata only)."""

    field_name: str
    description: str
    required: bool
    json_schema_value: bool = False
    json_schema_name: str | None = None
    json_schema: dict[str, Any] | None = None
    entity_schema: bool = False


@dataclass(init=False, frozen=True)
class FieldGraphNode(BaseGraphNode[FieldGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for one declared field under a host ``parent_type``.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(parent_type) + ':' + field_name.strip()``;
    :attr:`NODE_TYPE` is ``Field``; ``parent_type`` must be a ``type``;
    Interchange ``properties`` on the node carry ``required``, ``description`` (empty string when omitted),
    optional ``json_schema_value`` / ``json_schema_name`` / ``json_schema`` for :class:`~aoa.action_machine.model.json_schema_value.JsonSchemaValue` fields;
    optional ``entity_schema`` marks a concrete field with an outgoing entity link.
    :class:`FieldGraphPayload` mirrors those fields. No Pydantic graph walk inside this class (callers pass flags and schema copies).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Field"
    entity_schema_edge: EntitySchemaGraphEdge | None

    def __init__(
        self,
        parent_type: type,
        field_name: str,
        *,
        description: str | None = None,
        required: bool = False,
        json_schema_value: bool = False,
        json_schema_name: str | None = None,
        json_schema: dict[str, Any] | None = None,
        entity_schema_target: type | None = None,
    ) -> None:
        if not isinstance(parent_type, type):
            msg = f"parent_type must be a type, got {type(parent_type).__name__}"
            raise TypeError(msg)

        schema_copy = copy.deepcopy(json_schema) if json_schema is not None else None
        node_obj = FieldGraphPayload(
            field_name=field_name,
            description="" if description is None else description,
            required=required,
            json_schema_value=json_schema_value,
            json_schema_name=json_schema_name,
            json_schema=schema_copy,
            entity_schema=entity_schema_target is not None,
        )
        props: dict[str, Any] = {
            "required": required,
            "description": "" if description is None else description,
            "json_schema_value": json_schema_value,
            "entity_schema": entity_schema_target is not None,
        }
        if json_schema_name:
            props["json_schema_name"] = json_schema_name
        if schema_copy is not None:
            props["json_schema"] = copy.deepcopy(schema_copy)
        super().__init__(
            node_id=f"{TypeIntrospection.full_qualname(parent_type)}:{field_name.strip()}",
            node_type=FieldGraphNode.NODE_TYPE,
            label=field_name.strip(),
            properties=props,
            node_obj=node_obj,
        )
        edge = EntitySchemaGraphEdge(entity_cls=entity_schema_target) if entity_schema_target is not None else None
        object.__setattr__(self, "entity_schema_edge", edge)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "properties": {
                "required": bool(self.properties["required"]),
                "description": str(self.properties["description"]),
                "json_schema_value": bool(self.properties["json_schema_value"]),
                "entity_schema": bool(self.properties["entity_schema"]),
                **(
                    {"json_schema_name": str(self.properties["json_schema_name"])}
                    if "json_schema_name" in self.properties
                    else {}
                ),
                **(
                    {"json_schema": copy.deepcopy(self.properties["json_schema"])}
                    if self.properties.get("json_schema") is not None
                    else {}
                ),
            },
        }

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return the optional ``entity_schema`` edge from this concrete field to an entity node."""
        if self.entity_schema_edge is None:
            return []
        return [self.entity_schema_edge]
