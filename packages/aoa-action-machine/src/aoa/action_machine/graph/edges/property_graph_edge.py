# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/property_graph_edge.py
"""
PropertyGraphEdge — COMPOSITION from Params / Result → PropertyField interchange graph node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror computed / plain-property companions on params or result schemas: composition with
``edge_name`` ``property`` from an interchange graph node to a
:class:`~aoa.action_machine.graph.nodes.property_field_graph_node.PropertyFieldGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Params / Result (source id + type)  ──{property}──►  PropertyFieldGraphNode
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, get_type_hints

from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.composition_graph_edge import CompositionGraphEdge
from aoa.action_machine.graph.edges.entity_schema_graph_edge import (
    entity_schema_projection_target_from_annotation,
)
from aoa.action_machine.graph.nodes.property_field_graph_node import PropertyFieldGraphNode
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class PropertyGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge schema host (params or result) → property-field graph node.
    CONTRACT: ``edge_name`` literal ``property``; ``is_dag`` False; ``target_node`` wired when emitted.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        property_node: PropertyFieldGraphNode,
    ) -> None:
        super().__init__(
            edge_name="property",
            is_dag=False,
            target_node_id=property_node.node_id,
            target_node=property_node,
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
    def get_property_edges(cls, schema_cls: type, _source_host: BaseGraphNode[Any]) -> list[PropertyGraphEdge]:
        """Build composition edges from params or result host to computed/plain property nodes."""
        vertices = cls._property_graph_nodes_for_host(schema_cls)
        return [cls(property_node=p) for p in vertices]

    @classmethod
    def _property_graph_nodes_for_host(cls, host_cls: type) -> list[PropertyFieldGraphNode]:
        """One ``PropertyFieldGraphNode`` per Pydantic computed field and per plain ``property`` on the host class."""
        out: list[PropertyFieldGraphNode] = []
        seen: set[str] = set()

        model_fields = getattr(host_cls, "model_fields", None)
        model_field_names = set(model_fields) if isinstance(model_fields, Mapping) else set()

        try:
            hints = get_type_hints(host_cls, include_extras=True)
        except Exception:
            hints = {}

        model_computed_fields = getattr(host_cls, "model_computed_fields", None)
        if isinstance(model_computed_fields, Mapping):
            for prop_name, computed_info in model_computed_fields.items():
                seen.add(prop_name)
                annotation = hints.get(prop_name, getattr(computed_info, "return_type", None))
                out.append(
                    PropertyFieldGraphNode(
                        host_cls,
                        prop_name,
                        required=False,
                        entity_schema_target=entity_schema_projection_target_from_annotation(annotation),
                    ),
                )

        prop_members = TypeIntrospection.property_members(host_cls)
        for prop_name in sorted(prop_members):
            if prop_name in seen or prop_name in model_field_names:
                continue
            seen.add(prop_name)
            fget = prop_members[prop_name].fget
            fallback = None if fget is None else TypeIntrospection.callable_return_annotation(fget)
            annotation = hints.get(prop_name, fallback)
            out.append(
                PropertyFieldGraphNode(
                    host_cls,
                    prop_name,
                    required=False,
                    entity_schema_target=entity_schema_projection_target_from_annotation(annotation),
                ),
            )
        return out
