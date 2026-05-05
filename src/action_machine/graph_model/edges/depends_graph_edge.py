# src/action_machine/graph_model/edges/depends_graph_edge.py
"""
DependsGraphEdge — ASSOCIATION for ``@depends`` from Action → declared dependency type.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralizes ``@depends`` edge construction: ``edge_name`` ``@depends``, ``is_dag=True``,
``target_node`` stub until hydrated, and ``properties`` mirroring ``DependencyInfo``
(``description``, optional ``factory``) so runtime can reconstruct a
:class:`~action_machine.runtime.dependency_factory.DependencyFactory` from the graph.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@depends──►  Action | Resource | … (interchange id + type)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver
from action_machine.runtime.dependency_info import DependencyInfo
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode


class DependsGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge for ``@depends`` slots on an Action host.
    CONTRACT: ``edge_name`` ``@depends``, ``is_dag`` True; coordinator wires ``target_node`` for typed vertex reads.
    PROPERTIES: ``description`` (human text); optional ``factory`` callable (runtime-only); ``DependencyFactory.resolve`` forwards ``*args``, ``**kwargs`` when calling ``factory``.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        target_node_id: str,
        target_node: BaseGraphNode[Any] | None = None,
        description: str = "",
        factory: Callable[..., Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="@depends",
            is_dag=True,
            target_node_id=target_node_id,
            target_node=target_node,
            properties={"description": description, "factory": factory},
        )

    @staticmethod
    def get_dependency_edges(
        action_cls: type[Any],
    ) -> list[DependsGraphEdge]:
        """Return one typed edge per ``@depends`` declaration on ``action_cls``."""
        edges: list[DependsGraphEdge] = []
        for raw in DependsIntentResolver.resolve_dependency_infos(action_cls):
            if not isinstance(raw, DependencyInfo):
                msg = (
                    f"Expected DependencyInfo entries in {action_cls.__qualname__!r} "
                    f"_depends_info, got {type(raw).__name__}"
                )
                raise TypeError(msg)
            edges.append(
                DependsGraphEdge(
                    target_node_id=TypeIntrospection.full_qualname(raw.cls),
                    target_node=None,
                    description=raw.description,
                    factory=raw.factory,
                )
            )
        return edges
