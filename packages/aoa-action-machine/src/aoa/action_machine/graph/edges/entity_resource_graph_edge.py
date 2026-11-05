# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_resource_graph_edge.py
"""
EntityResourceGraphEdge — AGGREGATION from an entity to the one resource that stores it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An entity is a row stored by one resource (``@entity(resource=...)``). This edge makes
that walkable: a reader of the graph finds every entity of a resource — the data model
of one database — without inferring it from domains. Protocol 1.6 describes the edge;
"exactly one per entity" is AOA's rule, checked when the graph is built.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    EntityGraphNode  ──entity_resource──►  ResourceGraphNode  ──domain──►  DomainGraphNode
           └──────────────────────domain (the resource's)──────────────────────┘
"""

from __future__ import annotations

from typing import Any, ClassVar

from aoa.action_machine.graph.core.aggregation_graph_edge import AggregationGraphEdge
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class EntityResourceGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge ``entity → resource``.
    CONTRACT: ``edge_name`` ``entity_resource``; ``is_dag`` true; empty ``properties``; default edge id ``<entity>|entity_resource|<resource>``.
    INVARIANTS: One per entity node; ``target_node`` is wired by the coordinator from the resource's node.
    FAILURES: :exc:`~aoa.action_machine.exceptions.MissingEntityInfoError` from :meth:`from_entity` when ``@entity`` names no usable resource.
    AI-CORE-END
    """

    EDGE_TYPE: ClassVar[str] = "entity_resource"

    def __init__(self, resource_cls: type) -> None:
        super().__init__(
            edge_name=self.EDGE_TYPE,
            is_dag=True,
            target_node_id=TypeIntrospection.full_qualname(resource_cls),
            target_node=None,
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        """Serialize the edge as a protocol 1.6 row."""
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }

    @classmethod
    def from_entity(cls, entity_cls: type) -> EntityResourceGraphEdge:
        """Build the edge from the resource ``@entity`` names on ``entity_cls``."""
        return cls(EntityIntentResolver.resolve_resource_type(entity_cls))
