# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_field_graph_edge.py
"""
EntityFieldGraphEdge — COMPOSITION from ``EntityGraphNode`` to ``EntityFieldGraphNode``.

:meth:`get_entity_field_edges` materializes one edge per scalar model field (declaration order,
relations excluded); each edge wires the matching :class:`~aoa.action_machine.graph.nodes.entity_field_graph_node.EntityFieldGraphNode` as ``target_node``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.composition_graph_edge import CompositionGraphEdge
from aoa.action_machine.graph.nodes.entity_field_graph_node import EntityFieldGraphNode
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver


class EntityFieldGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge entity host → scalar field graph node.
    CONTRACT: ``EDGE_NAME`` literal ``entity_field``; ``is_dag`` False; ``properties`` carry ``ordinal`` and ``field_name`` (same as target ``label``). Static :meth:`get_entity_field_edges` builds entity scalar-field composition edges only.
    AI-CORE-END
    """

    EDGE_NAME: ClassVar[str] = "entity_field"

    def __init__(
        self,
        *,
        field_node: EntityFieldGraphNode,
        ordinal: int,
    ) -> None:
        if ordinal < 0:
            msg = "EntityFieldGraphEdge requires ordinal >= 0"
            raise ValueError(msg)

        name = field_node.label
        super().__init__(
            edge_name=EntityFieldGraphEdge.EDGE_NAME,
            is_dag=False,
            target_node_id=field_node.node_id,
            target_node=field_node,
            properties={"ordinal": ordinal, "field_name": name},
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {
                "ordinal": int(self.properties["ordinal"]),
                "field_name": str(self.properties["field_name"]),
            },
        }

    @staticmethod
    def get_entity_field_edges(entity_cls: type[BaseEntity]) -> list[EntityFieldGraphEdge]:
        """Return ``entity_field`` composition edges with wired :class:`EntityFieldGraphNode` targets (scalar fields only)."""
        relation_names = {rel.field_name for rel in EntityIntentResolver.resolve_entity_relations(entity_cls)}
        items: list[tuple[str, Any]] = [
            (name, fld.annotation) for name, fld in entity_cls.model_fields.items() if name not in relation_names
        ]
        if not any(name == "id" for name, _ in items):
            items.insert(0, ("id", str))

        edges: list[EntityFieldGraphEdge] = []
        for ordinal, (name, ann) in enumerate(items):
            node = EntityFieldGraphNode(entity_cls, name, annotation=ann)
            edges.append(EntityFieldGraphEdge(field_node=node, ordinal=ordinal))
        return edges
