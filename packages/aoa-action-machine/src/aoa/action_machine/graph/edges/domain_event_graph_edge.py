# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/domain_event_graph_edge.py
"""
DomainEventGraphEdge — AGGREGATION from a domain to an event of its vocabulary.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each event in a domain's ``events``, declared or inherited, becomes one ``domain_event`` edge.
A vocabulary holds its events without owning them, so one event may be in several domains.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.aggregation_graph_edge import AggregationGraphEdge
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class DomainEventGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge from a ``Domain`` node to an ``Event`` node.
    CONTRACT: ``edge_name`` ``domain_event``; ``is_dag`` False; empty ``properties``; ``target_node_id`` is the event's dotted class path.
    INVARIANTS: One edge per event in the domain's ``events``.
    AI-CORE-END
    """

    def __init__(self, event_cls: type[Any]) -> None:
        super().__init__(
            edge_name="domain_event",
            is_dag=False,
            target_node_id=TypeIntrospection.full_qualname(event_cls),
            target_node=None,
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

    @staticmethod
    def get_domain_event_edges(domain_cls: type[Any]) -> list[DomainEventGraphEdge]:
        """Return one edge per event in the ``events`` of ``domain_cls``."""
        return [DomainEventGraphEdge(event) for event in getattr(domain_cls, "events", ())]
