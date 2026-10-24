# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_reference_graph_edge.py
"""
EntityReferenceGraphEdge — ASSOCIATION from an entity host to the dictionary it references.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One edge per field whose resolved type is a closed dictionary. The field row already
carries ``reference_qualname``; the edge makes the reference walkable, so a consumer that
reads edges finds the dictionary the model declares instead of inferring it from a column.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    EntityGraphNode  ──entity_reference[field]──►  the dictionary's Entity node

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    The edge type, its properties, and the rule that builds one edge per accepted
    dictionary reference at the host's node construction.

**Out of scope**
    Refusing a field that states no reference — that belongs to
    :func:`~aoa.action_machine.graph.validators.entity_field_validator.validate_entity_fields`;
    the ERD projection — that belongs to ``aoa-maxitor``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.graph.nodes.entity_field_graph_node import declared_dictionary
from aoa.action_machine.intents.entity.entity_intent import entity_info_is_set
from aoa.action_machine.intents.entity.entity_relation_intent_resolver import is_relation_container
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class EntityReferenceGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge from an ``@entity`` host to the closed dictionary a field references.
    CONTRACT: ``edge_name`` ``entity_reference``; ``is_dag`` False; ``properties`` carry ``field_name`` and ``cardinality`` (``one``); ``target_node_id`` is the dictionary's interchange id.
    INVARIANTS: One edge per accepted dictionary reference; an edge is emitted only when the dictionary is a graph node, because the declaration rule refuses every other case.
    AI-CORE-END
    """

    EDGE_NAME: ClassVar[str] = "entity_reference"

    def __init__(
        self,
        *,
        target_node_id: str,
        field_name: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name=EntityReferenceGraphEdge.EDGE_NAME,
            is_dag=False,
            target_node_id=target_node_id,
            target_node=target_node,
            properties={"field_name": field_name, "cardinality": "one"},
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        """Return the edge row without callables or wired object references."""
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {
                "field_name": str(self.properties["field_name"]),
                "cardinality": str(self.properties["cardinality"]),
            },
        }

    @staticmethod
    def get_entity_reference_edges(entity_cls: type[BaseEntity]) -> list[EntityReferenceGraphEdge]:
        """Return one edge per field whose resolved type is a dictionary with a graph node."""
        edges: list[EntityReferenceGraphEdge] = []
        for field_name, field_info in entity_cls.model_fields.items():
            if is_relation_container(field_info.annotation):
                # A dictionary association routes through the ordinary relation path, never
                # through the special reference edge.
                continue
            dictionary = declared_dictionary(field_info.annotation)
            if dictionary is None or not entity_info_is_set(dictionary):
                continue
            if excluded_from_graph_model(dictionary):
                continue
            edges.append(
                EntityReferenceGraphEdge(
                    target_node_id=TypeIntrospection.full_qualname(dictionary),
                    field_name=field_name,
                ),
            )
        return edges
