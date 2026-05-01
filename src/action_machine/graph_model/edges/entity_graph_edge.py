# src/action_machine/graph_model/edges/entity_graph_edge.py
"""
EntityGraphEdge — ASSOCIATION for declarative entity→entity relation fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralizes relation edge construction: ``edge_name`` ``@entity_relation``, ``is_dag=True``,
rich ``properties`` from :class:`~action_machine.intents.entity.entity_relation_intent_resolver.EntityRelationIntentResolver`,
``target_node`` stub until hydrated.

Skips rows where ``omit_graph_edge`` is set (parity with legacy facet emission).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    EntityGraphNode  ──@entity_relation[field]──►  other ``BaseEntity`` class (interchange id)
"""

from __future__ import annotations

from typing import Any

from action_machine.domain.entity import BaseEntity
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from action_machine.intents.entity.entity_relation_intent_resolver import (
    EntityRelationIntentResolver,
)
from action_machine.system_core import TypeIntrospection
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
    CONTRACT: ``edge_name`` ``@entity_relation``, ``is_dag`` True; coordinator wires ``target_node``.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node_id: str,
        source_node: BaseGraphNode[Any],
        target_node_id: str,
        relation: EntityRelationIntentResolver,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="@entity_relation",
            is_dag=False,
            source_node_id=source_node_id,
            source_node=source_node,
            target_node_id=target_node_id,
            target_node=target_node,
            properties=_entity_relation_properties(relation),
        )

    @staticmethod
    def get_entity_relation_edges(
        source_node: BaseGraphNode[Any],
        entity_cls: type[BaseEntity],
    ) -> list[EntityGraphEdge]:
        """Return one typed edge per non-omitted entity relation declaration on ``entity_cls``."""
        return [
            EntityGraphEdge(
                source_node_id=source_node.node_id,
                source_node=source_node,
                relation=rel,
                target_node_id=TypeIntrospection.full_qualname(rel.target_entity),
                target_node=None,
            )
            for rel in EntityIntentResolver.resolve_entity_relations(entity_cls)
            if not rel.omit_graph_edge
        ]
