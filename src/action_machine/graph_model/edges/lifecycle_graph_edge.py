# src/action_machine/graph_model/edges/lifecycle_graph_edge.py
"""
LifeCycleGraphEdge — ASSOCIATION from an arbitrary interchange source to a ``Lifecycle`` subtype row.

Standalone edge type; coordinators may wire ``target_node`` later. Not registered in package lazy exports in this revision.
"""

from __future__ import annotations

from typing import Any

from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode


class LifeCycleGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge ``source → lifecycle_class`` interchange id.
    CONTRACT: ``edge_name`` ``lifecycle``; ``is_dag`` False (lifecycle-bearing subgraphs are not asserted acyclic globally); mandatory ``properties['field_name']``.
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

        super().__init__(
            edge_name="lifecycle",
            is_dag=False,
            source_node_id=source_node_id,
            source_node=source_node,
            target_node_id=TypeIntrospection.full_qualname(lifecycle_cls),
            target_node=target_node,
            properties={"field_name": needle},
        )
