# src/action_machine/graph_model/edges/depends_graph_edge.py
"""
DependsGraphEdge — ASSOCIATION for ``@depends`` from Action → declared dependency type.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralizes ``@depends`` edge construction: ``edge_name`` ``@depends``, ``is_dag=True``,
``target_node`` stub until hydrated.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@depends──►  Action | Resource | … (interchange id + type)
"""

from __future__ import annotations

from typing import Any

from action_machine.graph_model.nodes.resource_graph_node import ResourceGraphNode
from action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver
from action_machine.model.base_action import BaseAction
from action_machine.resources.base_resource import BaseResource
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode


class DependsGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge for ``@depends`` slots on an Action host.
    CONTRACT: ``edge_name`` ``@depends``, ``is_dag`` True; ``target_node_type`` set by caller per resolved dependency class.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node_id: str,
        source_node_type: str,
        source_node: BaseGraphNode[Any],
        target_node_id: str,
        target_node_type: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="@depends",
            is_dag=True,
            source_node_id=source_node_id,
            source_node_type=source_node_type,
            source_node=source_node,
            target_node_id=target_node_id,
            target_node_type=target_node_type,
            target_node=target_node,
        )

    @staticmethod
    def get_dependency_edges(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[DependsGraphEdge]:
        """Return one typed edge per ``@depends`` declaration on ``action_cls``."""
        return [
            DependsGraphEdge(
                source_node_id=source_node.node_id,
                source_node_type=source_node.node_type,
                source_node=source_node,
                target_node_id=TypeIntrospection.full_qualname(dependency_type),
                target_node_type=DependsGraphEdge._resolve_target_node_type(
                    source_node,
                    dependency_type,
                ),
                target_node=None,
            )
            for dependency_type in DependsIntentResolver.resolve_dependency_types(action_cls)
        ]

    @staticmethod
    def _resolve_target_node_type(source_node: BaseGraphNode[Any], target_cls: type) -> str:
        """Interchange ``target_node_type`` for an associated dependency target."""
        if issubclass(target_cls, BaseAction):
            return source_node.node_type
        if issubclass(target_cls, BaseResource):
            return ResourceGraphNode.NODE_TYPE
        return "UncknownTypeNode"
