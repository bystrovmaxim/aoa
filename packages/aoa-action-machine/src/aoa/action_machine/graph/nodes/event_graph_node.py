# packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/event_graph_node.py
"""
EventGraphNode — interchange node for ``BaseEvent`` classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One node per event class, shaped as a ``Params`` node: dotted class path as ``id``, class name
as ``label``, no properties of its own. Its fields are ``Field`` nodes and its class properties
``PropertyField`` nodes. The system fields say how a line was delivered, not what happened,
so they stay out of the graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, TypeVar

from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.field_graph_edge import FieldGraphEdge
from aoa.action_machine.graph.edges.property_graph_edge import PropertyGraphEdge
from aoa.action_machine.model.base_event import SYSTEM_FIELDS, BaseEvent
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

TEvent = TypeVar("TEvent", bound=BaseEvent)


@dataclass(init=False, frozen=True)
class EventGraphNode(BaseGraphNode[type[TEvent]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseEvent`` class.
    CONTRACT: Built from ``type[TEvent]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label; empty ``properties``; :attr:`fields` and :attr:`props` as on ``ParamsGraphNode``.
    INVARIANTS: The system fields of ``BaseEvent`` never become ``Field`` nodes.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Event"
    fields: list[FieldGraphEdge]
    props: list[PropertyGraphEdge]

    def __init__(self, event_cls: type[TEvent]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(event_cls),
            node_type=EventGraphNode.NODE_TYPE,
            label=event_cls.__name__,
            properties={},
            node_obj=event_cls,
        )
        own_fields = [
            edge
            for edge in FieldGraphEdge.get_field_edges(event_cls, self)
            if edge.target_node is None or edge.target_node.label not in SYSTEM_FIELDS
        ]
        object.__setattr__(self, "fields", own_fields)
        object.__setattr__(self, "props", PropertyGraphEdge.get_property_edges(event_cls, self))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "properties": {},
        }

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return the outgoing field and property composition edges."""
        return [*self.fields, *self.props]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Return the field and property nodes those edges point at."""
        return [edge.target_node for edge in self.get_all_edges() if edge.target_node is not None]
