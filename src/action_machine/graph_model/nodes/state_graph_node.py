# src/action_machine/graph_model/nodes/state_graph_node.py
"""
StateGraphNode — interchange vertex for one state slot under a lifecycle vertex.

``node_id`` is the parent :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`
interchange id plus ``:`` and the caller-supplied state key (trimmed).

Outgoing :class:`~action_machine.graph_model.edges.state_graph_edge.StateGraphEdge`
rows live in :attr:`lifecycle_transitions` and are returned from :meth:`~graph.base_graph_node.BaseGraphNode.get_all_edges`.

The parent :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode` exposes canonical vertices via :attr:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode.state_vertices` and flattens the **same instances** into
:attr:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode.states` /
:meth:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode.transition_edges` for convenience without duplicating graph assembly.

Constructed only via :meth:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode.state_companion_nodes` /
:meth:`~graph.base_graph_node.BaseGraphNode.get_companion_nodes` on the lifecycle interchange row (**not** by listing companions on this vertex).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from action_machine.domain.lifecycle import Lifecycle
from action_machine.graph_model.edges.state_graph_edge import StateGraphEdge
from action_machine.system_core import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

TLifecycle = TypeVar("TLifecycle", bound=Lifecycle)


@dataclass(frozen=True)
class StateGraphPayload:
    """Frozen payload for :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`."""

    lifecycle_class: type[Lifecycle]
    state_key: str
    lifecycle_graph_node_id: str


@dataclass(init=False, frozen=True)
class StateGraphNode(BaseGraphNode[StateGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange vertex for one state key scoped under the parent interchange row :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`.
    CONTRACT: ``node_id`` is ``lifecycle_graph_node_id.strip() + ':' + state_key.strip()``; ``label`` trimmed state key; ``properties`` carry ``lifecycle_class_id`` / ``state_key``; ``node_obj`` is :class:`StateGraphPayload` (``lifecycle_graph_node_id`` matches parent's ``node_id``).
    INVARIANTS: Frozen; :attr:`lifecycle_transitions` is the canonical outgoing edge list surfaced by ``get_all_edges``; :meth:`get_companion_nodes` is always empty (registration only through :class:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge`).
    FAILURES: :exc:`ValueError` when ``lifecycle_graph_node_id`` or ``state_key`` is blank after strip.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "State"
    lifecycle_transitions: list[StateGraphEdge] = field(init=False)

    def __init__(
        self,
        lifecycle_cls: type[TLifecycle],
        state_key: str,
        lifecycle_graph_node_id: str,
    ) -> None:
        parent_id = lifecycle_graph_node_id.strip()
        if not parent_id:
            raise ValueError("lifecycle_graph_node_id must be non-empty")

        key_stripped = state_key.strip()
        if not key_stripped:
            raise ValueError("state_key must be non-empty")

        payload = StateGraphPayload(
            lifecycle_class=lifecycle_cls,
            state_key=key_stripped,
            lifecycle_graph_node_id=parent_id,
        )

        super().__init__(
            node_id=f"{parent_id}:{key_stripped}",
            node_type=StateGraphNode.NODE_TYPE,
            label=key_stripped,
            properties={
                "lifecycle_class_id": TypeIntrospection.full_qualname(lifecycle_cls),
                "state_key": key_stripped,
            },
            node_obj=payload,
        )
        object.__setattr__(self, "lifecycle_transitions", StateGraphNode._build_lifecycle_transition_edges(self))

    @staticmethod
    def _build_lifecycle_transition_edges(vertex: StateGraphNode) -> list[StateGraphEdge]:
        tpl = vertex.node_obj.lifecycle_class._get_template()
        if tpl is None:
            return []

        nid_root = vertex.node_obj.lifecycle_graph_node_id
        state_info = tpl.get_states().get(vertex.node_obj.state_key)
        if state_info is None:
            return []

        return [
            StateGraphEdge(
                target_node_id=f"{nid_root}:{to_key}",
                from_state=vertex.node_obj.state_key,
                to_state=to_key,
                target_node=None,
            )
            for to_key in state_info.transitions
        ]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Status vertices are never self-registering companions; use :class:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge` + :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`."""
        return []

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return [*self.lifecycle_transitions]
