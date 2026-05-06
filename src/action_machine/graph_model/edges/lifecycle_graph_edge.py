# src/action_machine/graph_model/edges/lifecycle_graph_edge.py
"""
LifeCycleGraphEdge — ASSOCIATION from entity (or host) interchange row to one ``Lifecycle`` field vertex.

Wiring ``target_node`` to :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`
aligns ``target_node_id`` with ``:lifecycle:`` interchange ids.

:meth:`~LifeCycleGraphEdge.get_lifecycle_edges` returns association edges with wired lifecycle vertices.
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
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode


class LifeCycleGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge from an entity host interchange row to a lifecycle field vertex.
    CONTRACT: ``edge_name`` ``lifecycle``; ``is_dag`` False; mandatory ``properties['field_name']``; optional wired ``LifeCycleGraphNode`` as ``target_node`` (else target id is lifecycle class dotted name). Static :meth:`get_lifecycle_edges` builds entity lifecycle associations only; state companions and transitions live on lifecycle/state nodes.
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

    @staticmethod
    @cache  # keyed by ``entity_cls`` so repeated entity nodes share lifecycle target instances
    def get_lifecycle_edges(entity_cls: type[BaseEntity]) -> list[LifeCycleGraphEdge]:
        """``lifecycle`` associations (wired :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode` targets) for every declared field."""
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
        return associations
