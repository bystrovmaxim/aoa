# packages/aoa-action-machine/src/aoa/action_machine/graph_model/edges/lifecycle_graph_edge.py
"""
LifeCycleGraphEdge — COMPOSITION from entity (or host) interchange row to one ``Lifecycle`` field graph node.

Wiring ``target_node`` to :class:`~aoa.action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`
aligns ``target_node_id`` with ``:lifecycle:`` interchange ids.

:meth:`~LifeCycleGraphEdge.get_lifecycle_edges` returns composition edges with wired lifecycle graph nodes.
Those lifecycle graph nodes own state companions and template ``lifecycle_transition`` rows.
Interchange companions for state graph nodes are chained only via :class:`~aoa.action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode` reachable from ``LifeCycleGraphEdge.target_node``.
:class:`~aoa.action_machine.graph_model.nodes.state_graph_node.StateGraphNode` rows never advertise companions.
"""

from __future__ import annotations

from functools import cache
from typing import Any, ClassVar

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph_model.nodes.lifecycle_graph_node import LifeCycleGraphNode
from aoa.action_machine.intents.entity.lifecycle_intent_resolver import LifeCycleIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.composition_graph_edge import CompositionGraphEdge


class LifeCycleGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge from an entity host interchange row to a lifecycle field graph node.
    CONTRACT: ``edge_name`` ``lifecycle``; ``is_dag`` False; mandatory ``properties['field_name']``; optional wired ``LifeCycleGraphNode`` as ``target_node`` (else target id is lifecycle class dotted name). Static :meth:`get_lifecycle_edges` builds entity lifecycle composition edges only; state companions and transitions live on lifecycle/state nodes.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    FAILURES: :exc:`ValueError` when ``field_name`` is blank after strip.
    AI-CORE-END
    """

    EDGE_NAME: ClassVar[str] = "lifecycle"

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
            edge_name=LifeCycleGraphEdge.EDGE_NAME,
            is_dag=False,
            target_node_id=target_id,
            target_node=target_node,
            properties={"field_name": needle},
        )

    @staticmethod
    @cache  # keyed by ``entity_cls`` so repeated entity nodes share lifecycle target instances
    def get_lifecycle_edges(entity_cls: type[BaseEntity]) -> list[LifeCycleGraphEdge]:
        """``lifecycle`` composition edges (wired :class:`~aoa.action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode` targets) for every declared field."""
        out: list[LifeCycleGraphEdge] = []
        for row in LifeCycleIntentResolver.resolve_lifecycle_fields(entity_cls):
            target_lifecycle_node = LifeCycleGraphNode(entity_cls, row.field_name, row.lifecycle_class)
            out.append(
                LifeCycleGraphEdge(
                    lifecycle_cls=row.lifecycle_class,
                    field_name=row.field_name,
                    target_node=target_lifecycle_node,
                ),
            )
        return out
