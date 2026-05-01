# src/action_machine/graph_model/edges/lifecycle_graph_edge.py
"""
LifeCycleGraphEdge — ASSOCIATION from entity (or host) interchange row to one ``Lifecycle`` field vertex.

Wiring ``target_node`` to :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`
aligns ``target_node_id`` with ``:lifecycle:`` interchange ids.

:meth:`~LifeCycleGraphEdge.get_lifecycle_association_edges` returns association edges with wired lifecycle vertices.
Those lifecycle vertices own state companions and template ``lifecycle_transition`` rows.
Interchange companions for status vertices are chained only via :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode` reachable from ``LifeCycleGraphEdge.target_node``.
:class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode` rows never advertise companions.
"""

from __future__ import annotations

from functools import cache
from typing import Any

from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.nodes.lifecycle_graph_node import LifeCycleGraphNode
from action_machine.intents.entity.lifecycle_intent_resolver import LifeCycleIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode

from .state_graph_edge import StateGraphEdge


class LifeCycleGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge from an entity host interchange row to a lifecycle field vertex.
    CONTRACT: ``edge_name`` ``lifecycle``; ``is_dag`` False; mandatory ``properties['field_name']``; optional wired ``LifeCycleGraphNode`` as ``target_node`` (else target id is lifecycle class dotted name). Static :meth:`get_lifecycle_association_edges` builds entity lifecycle associations only; state companions and transitions live on lifecycle/state nodes.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    FAILURES: :exc:`ValueError` when ``field_name`` is blank after strip.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        lifecycle_cls: type,
        field_name: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        needle = field_name.strip()
        if not needle:
            raise ValueError("LifeCycleGraphEdge requires a non-empty field_name")

        if target_node is not None:
            target_id = target_node.node_id
        else:
            target_id = TypeIntrospection.full_qualname(lifecycle_cls)

        super().__init__(
            edge_name="lifecycle",
            is_dag=False,
            target_node_id=target_id,
            target_node=target_node,
            properties={"field_name": needle},
        )

    def state_transition_edges(self) -> list[StateGraphEdge]:
        """One :class:`StateGraphEdge` per outgoing template arc when ``target_node`` is a ``LifeCycleGraphNode``; otherwise empty."""
        target = self.target_node
        if target is None:
            return []
        if not isinstance(target, LifeCycleGraphNode):
            return []
        return LifeCycleGraphEdge.state_transition_edges_from_lifecycle_vertex(target)

    @staticmethod
    def state_transition_edges_from_lifecycle_vertex(
        lifecycle_vertex: LifeCycleGraphNode,
    ) -> list[StateGraphEdge]:
        """Flatten companion ``lifecycle_transition`` arcs tied to vertex ``states``."""
        return [
            edge
            for state_row in lifecycle_vertex.states
            for edge in state_row.lifecycle_transitions
        ]

    @staticmethod
    def get_lifecycle_association_edges(entity_cls: type[BaseEntity]) -> tuple[LifeCycleGraphEdge, ...]:
        """``lifecycle`` associations (wired :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode` targets) for every declared field."""
        return _materialize_entity_lifecycle_associations(entity_cls)


@cache  # keyed by ``entity_cls`` so repeated entity nodes share lifecycle target instances
def _materialize_entity_lifecycle_associations(
    entity_cls: type[BaseEntity],
) -> tuple[LifeCycleGraphEdge, ...]:
    associations: list[LifeCycleGraphEdge] = []
    for row in LifeCycleIntentResolver.resolve_lifecycle_fields(entity_cls):
        target_vertex = LifeCycleGraphNode(entity_cls, row.field_name, row.lifecycle_class)
        associations.append(
            LifeCycleGraphEdge(
                lifecycle_cls=row.lifecycle_class,
                field_name=row.field_name,
                target_node=target_vertex,
            ),
        )
    return tuple(associations)
