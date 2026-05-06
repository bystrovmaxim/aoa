# src/action_machine/graph_model/nodes/lifecycle_graph_node.py
"""
LifeCycleGraphNode — interchange vertex for one ``Lifecycle``-typed field on a host class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one
declared lifecycle field on a host type (typically an ``@entity`` class).
``node_id`` is ``<host_qualname>:lifecycle:<field_name>``; ``node_obj`` is a
frozen :class:`LifeCycleGraphPayload` with host class, trimmed field key, and
caller-supplied lifecycle subtype class.

Template states are attached via ``lifecycle_contains_state`` edges; transitions are modeled on
companion :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode` rows.
The parent lifecycle row keeps canonical companions in :attr:`~LifeCycleGraphNode.states`
(each a :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode`);
:meth:`~LifeCycleGraphNode.get_all_edges` returns transition edges from all of those state rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar, cast

from action_machine.domain.lifecycle import Lifecycle
from action_machine.graph_model.edges.lifecycle_state_graph_edge import LifeCycleStateGraphEdge
from action_machine.graph_model.nodes.state_graph_node import StateGraphNode
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

TLifecycle = TypeVar("TLifecycle", bound=Lifecycle)


@dataclass(frozen=True)
class LifeCycleGraphPayload:
    """Frozen payload for :attr:`~graph.base_graph_node.BaseGraphNode.node_obj` on a lifecycle interchange row."""

    host_cls: type[Any]
    field_name: str
    lifecycle_class: type[Lifecycle]


@dataclass(init=False, frozen=True)
class LifeCycleGraphNode(BaseGraphNode[LifeCycleGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange vertex for one lifecycle-declared slot on ``host_cls``; **child interchange graph** is carried by companions of type :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode`.
    CONTRACT: ``node_id`` is ``full_qualname(host_cls) + ':lifecycle:' + field_name.strip()``; ``label`` trimmed field key; ``properties['field_name']`` mirrors the trimmed field key; ``lifecycle_class`` supplied by caller; ``node_obj`` is :class:`LifeCycleGraphPayload`. Canonical state rows live in :attr:`states`; :meth:`get_companion_nodes` returns :attr:`states` typed as base interchange companions. Each state ``node_id`` is ``<this.node_id>:<state_key>`` (same root as :attr:`~action_machine.graph_model.nodes.state_graph_node.StateGraphPayload.lifecycle_graph_node_id` on each companion's ``node_obj``).
    EDGES: :meth:`get_all_edges` returns one ``lifecycle_contains_state`` edge for every row in :attr:`states` plus every ``lifecycle_transition`` edge exposed by those state rows.
    INVARIANTS: Frozen interchange row; :attr:`states` list is filled once via :meth:`~action_machine.graph_model.edges.lifecycle_state_graph_edge.LifeCycleStateGraphEdge.get_state_edges` (**do not mutate** ``states`` nor its elements externally).
    FAILURES: :exc:`ValueError` when ``field_name`` is blank after strip.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "lifecycle"
    states: list[StateGraphNode] = field(init=False)

    def __init__(
        self,
        host_cls: type[Any],
        field_name: str,
        lifecycle_cls: type[TLifecycle],
    ) -> None:
        needle = field_name.strip()
        if not needle:
            raise ValueError("LifeCycleGraphNode requires a non-empty field_name")

        super().__init__(
            node_id=f"{TypeIntrospection.full_qualname(host_cls)}:lifecycle:{needle}",
            node_type=LifeCycleGraphNode.NODE_TYPE,
            label=needle,
            properties={"field_name": needle},
            node_obj=LifeCycleGraphPayload(
                host_cls=host_cls,
                field_name=needle,
                lifecycle_class=lifecycle_cls,
            ),
        )
        object.__setattr__(self, "states", LifeCycleStateGraphEdge.get_state_edges(lifecycle_cls, self.node_id))

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Template state interchange rows (:attr:`states`)."""
        return cast("list[BaseGraphNode[Any]]", self.states)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Attach all state rows and surface every state-row ``lifecycle_transition`` edge."""
        return [
            *(LifeCycleStateGraphEdge(state_node) for state_node in self.states),
            *(
                edge
                for state_row in self.states
                for edge in state_row.get_all_edges()
            ),
        ]
