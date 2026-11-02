# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/emits_graph_edge.py
"""
EmitsGraphEdge — ASSOCIATION from an emitting method to an event it may emit.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each event in a method's ``@emits`` becomes one ``@emits`` edge. A method names an event and
does not own it, and one event has many emitters, so the edge is an association.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.intents.emits.emits_decorator import EMITS_ATTR
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class EmitsGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge from an emitting method to an ``Event`` node.
    CONTRACT: ``edge_name`` ``@emits``; ``is_dag`` False; empty ``properties``; ``target_node_id`` is the event's dotted class path.
    INVARIANTS: One edge per event in the ``@emits`` of a method that has a node.
    AI-CORE-END
    """

    def __init__(self, event_cls: type[Any]) -> None:
        super().__init__(
            edge_name="@emits",
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
    def get_emits_edges(method: Callable[..., Any]) -> list[EmitsGraphEdge]:
        """Return one edge per event ``method`` declares."""
        return [EmitsGraphEdge(event) for event in getattr(method, EMITS_ATTR, ())]
