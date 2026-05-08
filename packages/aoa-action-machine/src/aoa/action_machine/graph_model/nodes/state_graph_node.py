# packages/aoa-action-machine/src/aoa/action_machine/graph_model/nodes/state_graph_node.py
"""
StateGraphNode — interchange graph node for one state slot under a lifecycle graph node.

``node_id`` is the parent :class:`~aoa.action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`
interchange id plus ``:`` and the caller-supplied state key (trimmed).

Outgoing :class:`~aoa.action_machine.graph_model.edges.state_graph_edge.StateGraphEdge`
rows live in :attr:`lifecycle_transitions` and are returned from :meth:`~aoa.graph.base_graph_node.BaseGraphNode.get_all_edges`.

The parent :class:`~aoa.action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode` keeps companion rows in :attr:`~aoa.action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode.states`; :meth:`~aoa.action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode.get_all_edges` flattens the **same instances** carried here in :attr:`lifecycle_transitions`.

Constructed only via :meth:`~aoa.action_machine.graph_model.edges.lifecycle_state_graph_edge.LifeCycleStateGraphEdge.get_state_edges`
or equivalent wiring onto the parent lifecycle interchange row (**not** by listing companions on this graph node).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from aoa.action_machine.domain.exceptions import LifecycleGraphError
from aoa.action_machine.domain.lifecycle import Lifecycle, StateType
from aoa.action_machine.graph_model.edges.state_graph_edge import StateGraphEdge
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.base_graph_node import BaseGraphNode

TLifecycle = TypeVar("TLifecycle", bound=Lifecycle)


@dataclass(frozen=True)
class StateGraphPayload:
    """Frozen payload for :attr:`~aoa.graph.base_graph_node.BaseGraphNode.node_obj`."""

    lifecycle_class: type[Lifecycle]
    state_key: str
    lifecycle_graph_node_id: str


@dataclass(init=False, frozen=True)
class StateGraphNode(BaseGraphNode[StateGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange graph node for one state key scoped under the parent interchange row :class:`~aoa.action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`.
    CONTRACT: ``node_id`` is ``lifecycle_graph_node_id.strip() + ':' + state_key.strip()``; ``node_type`` mirrors ``StateInfo.state_type`` on the lifecycle template; ``label`` trimmed state key; ``properties`` carry ``lifecycle_class_id`` / ``state_key``; ``node_obj`` is :class:`StateGraphPayload` (``lifecycle_graph_node_id`` matches parent's ``node_id``).
    INVARIANTS: Frozen; :attr:`lifecycle_transitions` lists transitions from :meth:`~aoa.action_machine.graph_model.edges.state_graph_edge.StateGraphEdge.get_lifecycle_transition_edges` and is surfaced by ``get_all_edges``; :meth:`get_companion_nodes` is always empty (lifecycle rows register via ``LifeCycleGraphEdge``).
    FAILURES: :exc:`ValueError` when ``lifecycle_graph_node_id`` or ``state_key`` is blank after strip; :exc:`LifecycleGraphError` when the lifecycle class has no template or ``state_key`` is missing from that template.
    AI-CORE-END
    """

    NODE_TYPE_STATE_FINAL: ClassVar[str] = "StateFinal"
    NODE_TYPE_STATE_INTERMEDIATE: ClassVar[str] = "StateIntermediate"
    NODE_TYPE_STATE_INITIAL: ClassVar[str] = "StateInitial"
    lifecycle_transitions: list[StateGraphEdge] = field(init=False)

    @classmethod
    def _node_type_for_lifecycle_state_key(
        cls,
        lifecycle_cls: type[Lifecycle],
        state_key: str,
    ) -> str:
        """Resolve graph ``node_type`` from the lifecycle class template and ``state_key``."""
        tpl = lifecycle_cls._get_template()
        if tpl is None:
            msg = (
                f"{lifecycle_cls.__qualname__} has no lifecycle template; "
                f"cannot classify state {state_key!r} for graph node_type"
            )
            raise LifecycleGraphError(msg)
        info = tpl.get_states().get(state_key)
        if info is None:
            msg = (
                f"Lifecycle template for {lifecycle_cls.__qualname__!r} "
                f"has no StateInfo for state key {state_key!r}"
            )
            raise LifecycleGraphError(msg)
        match info.state_type:
            case StateType.INITIAL:
                return cls.NODE_TYPE_STATE_INITIAL
            case StateType.INTERMEDIATE:
                return cls.NODE_TYPE_STATE_INTERMEDIATE
            case StateType.FINAL:
                return cls.NODE_TYPE_STATE_FINAL

    def __init__(
        self,
        lifecycle_cls: type[TLifecycle],
        state_key: str,
        lifecycle_graph_node_id: str,
    ) -> None:
        """Wire ``node_id``, template-derived ``node_type``, payload, and outbound transition edges."""
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

        node_type_str = type(self)._node_type_for_lifecycle_state_key(lifecycle_cls, key_stripped)

        super().__init__(
            node_id=f"{parent_id}:{key_stripped}",
            node_type=node_type_str,
            label=key_stripped,
            properties={
                "lifecycle_class_id": TypeIntrospection.full_qualname(lifecycle_cls),
                "state_key": key_stripped,
            },
            node_obj=payload,
        )
        object.__setattr__(self, "lifecycle_transitions", StateGraphEdge.get_lifecycle_transition_edges(self))

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """State rows attach via ``LifeCycleGraphEdge``, not standalone companion registrations."""
        return []

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return template-defined ``lifecycle_transition`` edges originating at this state row."""
        return [*self.lifecycle_transitions]
