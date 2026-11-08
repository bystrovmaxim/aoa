# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/resource_entity_graph_edge.py
"""
ResourceEntityGraphEdge — AGGREGATION from a database to one of the entities it holds.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource **is** a database: it lists the entities that lie in it through
``@entities(*entity_classes)``. This edge makes that list walkable in the graph — a
reader finds every entity of a database without inferring it from domains, and an
entity may lie in two databases (a replica or a projection) without a refusal.

One edge per listed entity, from the resource node to the entity node. The default
edge id is ``<resource>|resource_entity|<entity>``; "one per ``@entities`` entry" is
AOA's rule, checked when the graph is built.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ResourceGraphNode  ──resource_entity──►  EntityGraphNode  ──domain──►  DomainGraphNode
"""

from __future__ import annotations

from typing import Any, ClassVar

from aoa.action_machine.graph.core.aggregation_graph_edge import AggregationGraphEdge
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class ResourceEntityGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge ``resource → entity``.
    CONTRACT: ``edge_name`` ``resource_entity``; ``is_dag`` true; empty ``properties``; default edge id ``<resource>|resource_entity|<entity>``.
    INVARIANTS: One per entity a resource lists with ``@entities``; ``target_node`` is wired by the coordinator when the entity node is present in the graph.
    FAILURES: :exc:`TypeError` when ``entity_cls`` is not a class.
    AI-CORE-END
    """

    EDGE_TYPE: ClassVar[str] = "resource_entity"

    def __init__(self, entity_cls: type) -> None:
        super().__init__(
            edge_name=self.EDGE_TYPE,
            is_dag=True,
            target_node_id=TypeIntrospection.full_qualname(entity_cls),
            target_node=None,
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        """Serialize the edge as a protocol 2.0 row."""
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }
