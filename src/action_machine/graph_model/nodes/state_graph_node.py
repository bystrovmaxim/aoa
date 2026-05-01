# src/action_machine/graph_model/nodes/state_graph_node.py
"""
StateGraphNode — interchange vertex for one state slot under a lifecycle vertex.

``node_id`` is the parent :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`
interchange id plus ``:`` and the caller-supplied state key (trimmed).

Standalone building block for coordinator wiring later (not emitted by inspectors in this revision).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar

from action_machine.domain.lifecycle import Lifecycle
from action_machine.system_core import TypeIntrospection
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
    ROLE: Interchange vertex for one state key scoped under a lifecycle vertex.
    CONTRACT: ``node_id`` is ``lifecycle_graph_node_id.strip() + ':' + state_key.strip()``; ``label`` trimmed state key; ``properties`` carry ``lifecycle_class_id`` / ``state_key``; ``node_obj`` is :class:`StateGraphPayload`.
    INVARIANTS: Frozen; emits no outgoing edges by default (does not introspect lifecycle templates).
    FAILURES: :exc:`ValueError` when ``lifecycle_graph_node_id`` or ``state_key`` is blank after strip.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "State"

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
