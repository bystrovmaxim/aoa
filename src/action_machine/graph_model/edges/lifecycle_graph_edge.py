# src/action_machine/graph_model/edges/lifecycle_graph_edge.py
"""
LifeCycleGraphEdge — ASSOCIATION from entity (or host) interchange row to one ``Lifecycle`` field vertex.

Wiring ``target_node`` to :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`
aligns ``target_node_id`` with ``:lifecycle:`` interchange ids.

:meth:`get_lifecycle_edges` returns association rows followed by composed
:class:`~action_machine.graph_model.edges.state_graph_edge.StateGraphEdge` arcs for each field.
Callers attach **associations only** from an :class:`~action_machine.graph_model.nodes.entity_graph_node.EntityGraphNode` row (:meth:`~graph.base_graph_node.BaseGraphNode.get_all_edges`).
Interchange companions for status vertices are chained only via :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode` reachable from ``LifeCycleGraphEdge.target_node``.
:class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode` rows never advertise companions.
"""

from __future__ import annotations

from typing import Any

from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.nodes.lifecycle_graph_node import LifeCycleGraphNode
from action_machine.intents.entity.lifecycle_intent_resolver import LifeCycleIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

from .state_graph_edge import StateGraphEdge


class LifeCycleGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge ``source → lifecycle`` field interchange row.
    CONTRACT: ``edge_name`` ``lifecycle``; ``is_dag`` False; mandatory ``properties['field_name']``; optional wired ``LifeCycleGraphNode`` as ``target_node`` (else target id is lifecycle class dotted name). Static :meth:`get_lifecycle_edges` attaches associations then each wired vertex's :class:`~action_machine.graph_model.edges.state_graph_edge.StateGraphEdge` transition rows for consumers that need one list.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    FAILURES: :exc:`ValueError` when ``field_name`` is blank after strip.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node_id: str,
        source_node: BaseGraphNode[Any],
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
            source_node_id=source_node_id,
            source_node=source_node,
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
    def get_lifecycle_edges(
        source_node: BaseGraphNode[Any],
        entity_cls: type[BaseEntity],
    ) -> list[BaseGraphEdge]:
        """``lifecycle`` associations with wired vertices, then every ``lifecycle_transition`` for each field."""
        out: list[BaseGraphEdge] = []
        for row in LifeCycleIntentResolver.resolve_lifecycle_fields(entity_cls):
            target_vertex = LifeCycleGraphNode(entity_cls, row.field_name, row.lifecycle_class)
            out.append(
                LifeCycleGraphEdge(
                    source_node_id=source_node.node_id,
                    source_node=source_node,
                    lifecycle_cls=row.lifecycle_class,
                    field_name=row.field_name,
                    target_node=target_vertex,
                ),
            )
            out.extend(target_vertex.transition_edges())
        return out
