# src/action_machine/graph_model/edges/lifecycle_graph_edge.py
"""
LifeCycleGraphEdge — ASSOCIATION from entity (or host) interchange row to one ``Lifecycle`` field vertex.

Wiring ``target_node`` to :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`
aligns ``target_node_id`` with ``:lifecycle:`` interchange ids.

:meth:`~LifeCycleGraphEdge.get_lifecycle_association_edges` /
:meth:`~LifeCycleGraphEdge.get_lifecycle_transition_edges` return disjoint slices backed by **one memoized materialization**
per ``entity_cls`` so lifecycle vertices referenced from associations remain the canonical owners of the returned ``lifecycle_transition`` rows.
:class:`~action_machine.graph_model.nodes.entity_graph_node.EntityGraphNode` stores associations on :attr:`~action_machine.graph_model.nodes.entity_graph_node.EntityGraphNode.lifecycles` and those transition edges on :attr:`~action_machine.graph_model.nodes.entity_graph_node.EntityGraphNode.states`.
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
    CONTRACT: ``edge_name`` ``lifecycle``; ``is_dag`` False; mandatory ``properties['field_name']``; optional wired ``LifeCycleGraphNode`` as ``target_node`` (else target id is lifecycle class dotted name). Static accessors :meth:`get_lifecycle_association_edges` and :meth:`get_lifecycle_transition_edges` split artifacts without exposing a merged list.
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
        """
        Delegate to :meth:`LifeCycleGraphNode.transition_edges` (same :class:`StateGraphEdge` rows).

        Kept for callers that only hold a vertex reference.
        """
        return lifecycle_vertex.transition_edges()

    @staticmethod
    def get_lifecycle_association_edges(entity_cls: type[BaseEntity]) -> tuple[LifeCycleGraphEdge, ...]:
        """``lifecycle`` associations (wired :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode` targets) for every declared field."""
        assoc, _ = _materialize_entity_lifecycle_slices(entity_cls)
        return assoc

    @staticmethod
    def get_lifecycle_transition_edges(entity_cls: type[BaseEntity]) -> tuple[StateGraphEdge, ...]:
        """All template ``lifecycle_transition`` rows spanning every lifecycle field (same instances as on those vertices)."""
        _, transitions = _materialize_entity_lifecycle_slices(entity_cls)
        return transitions


@cache  # keyed by ``entity_cls`` — shared by lifecycle association / transition accessors
def _materialize_entity_lifecycle_slices(
    entity_cls: type[BaseEntity],
) -> tuple[tuple[LifeCycleGraphEdge, ...], tuple[StateGraphEdge, ...]]:
    associations: list[LifeCycleGraphEdge] = []
    transitions: list[StateGraphEdge] = []
    for row in LifeCycleIntentResolver.resolve_lifecycle_fields(entity_cls):
        target_vertex = LifeCycleGraphNode(entity_cls, row.field_name, row.lifecycle_class)
        associations.append(
            LifeCycleGraphEdge(
                lifecycle_cls=row.lifecycle_class,
                field_name=row.field_name,
                target_node=target_vertex,
            ),
        )
        transitions.extend(target_vertex.transition_edges())
    return tuple(associations), tuple(transitions)
