# src/action_machine/graph_model/edges/entity_graph_edge.py
"""
EntityGraphEdge — ASSOCIATION for declarative entity→entity relation fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralizes relation edge construction: ``edge_name`` ``entity_relation`` (slot id, like ``domain`` — not a decorator),
``is_dag=False`` (entity graphs may contain cycles),
rich ``properties`` from :class:`~action_machine.intents.entity.entity_relation_intent_resolver.EntityRelationIntentResolver`,
``target_node`` stub until hydrated.

Skips rows where ``omit_graph_edge`` is set (parity with legacy interchange emission).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    EntityGraphNode  ──entity_relation[field]──►  other ``BaseEntity`` class (interchange id)
"""

from __future__ import annotations

from typing import Any

from action_machine.domain.entity import BaseEntity
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from action_machine.intents.entity.entity_relation_intent_resolver import EntityRelationIntentResolver
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode


def _entity_relation_properties(rel: EntityRelationIntentResolver) -> dict[str, Any]:
    props: dict[str, Any] = {
        "field_name": rel.field_name,
        "relation_type": rel.relation_type,
        "cardinality": rel.cardinality,
        "description": rel.description,
        "has_inverse": rel.has_inverse,
        "deprecated": rel.deprecated,
    }
    if rel.inverse_entity is not None:
        props["inverse_entity_id"] = TypeIntrospection.full_qualname(rel.inverse_entity)
    if rel.inverse_field:
        props["inverse_field"] = rel.inverse_field
    return props


class EntityGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge for declarative relation fields on an ``@entity`` host.
    CONTRACT: ``edge_name`` ``entity_relation``; ``is_dag`` False; coordinator wires ``target_node``.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        target_node_id: str,
        relation: EntityRelationIntentResolver,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="entity_relation",
            is_dag=False,
            target_node_id=target_node_id,
            target_node=target_node,
            properties=_entity_relation_properties(relation),
        )

    @staticmethod
    def get_entity_relation_edges(
        entity_cls: type[BaseEntity],
    ) -> list[EntityGraphEdge]:
        """Return one typed edge per non-omitted entity relation declaration on ``entity_cls``."""
        return [
            EntityGraphEdge(
                relation=rel,
                target_node_id=TypeIntrospection.full_qualname(rel.target_entity),
                target_node=None,
            )
            for rel in EntityIntentResolver.resolve_entity_relations(entity_cls)
            if not rel.omit_graph_edge
        ]
