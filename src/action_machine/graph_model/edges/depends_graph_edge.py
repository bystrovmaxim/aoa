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

from typing import Any, cast

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
    CONTRACT: ``edge_name`` ``@depends``, ``is_dag`` True; ``target_node_type`` derives from wired ``target_node`` or from ``@depends`` resolution when stubs omit it.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node_id: str,
        source_node: BaseGraphNode[Any],
        target_node_id: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="@depends",
            is_dag=True,
            source_node_id=source_node_id,
            source_node=source_node,
            target_node_id=target_node_id,
            target_node=target_node,
        )

    @property
    def target_node_type(self) -> str:
        if self.target_node is not None:
            return cast(str, self.target_node.node_type)
        src = self.source_node
        if src is None:
            msg = (
                "DependsGraphEdge: source_node is unset; "
                "cannot derive target_vertex_type without target_node."
            )
            raise RuntimeError(msg)
        action_cls = DependsGraphEdge._action_cls_from_edge_source(src)
        for dep_cls in DependsIntentResolver.resolve_dependency_types(action_cls):
            if TypeIntrospection.full_qualname(dep_cls) == self.target_node_id:
                return DependsGraphEdge._resolve_target_node_type(src, dep_cls)
        msg = (
            f"DependsGraphEdge: no dependency class matches target_node_id {self.target_node_id!r} "
            f"for action {TypeIntrospection.full_qualname(action_cls)}."
        )
        raise RuntimeError(msg)

    @staticmethod
    def get_dependency_edges(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[DependsGraphEdge]:
        """Return one typed edge per ``@depends`` declaration on ``action_cls``."""
        return [
            DependsGraphEdge(
                source_node_id=source_node.node_id,
                source_node=source_node,
                target_node_id=TypeIntrospection.full_qualname(dependency_type),
                target_node=None,
            )
            for dependency_type in DependsIntentResolver.resolve_dependency_types(action_cls)
        ]

    @staticmethod
    def _action_cls_from_edge_source(source_node: BaseGraphNode[Any]) -> type[Any]:
        obj = getattr(source_node, "node_obj", None)
        if isinstance(obj, type):
            return obj
        msg = (
            f"DependsGraphEdge: interchange source {source_node.node_id!r} "
            f"expects node_obj action class."
        )
        raise TypeError(msg)

    @staticmethod
    def _resolve_target_node_type(source_node: BaseGraphNode[Any], target_cls: type) -> str:
        """Interchange ``target_node_type`` for an associated dependency target."""
        if issubclass(target_cls, BaseAction):
            return source_node.node_type
        if issubclass(target_cls, BaseResource):
            return ResourceGraphNode.NODE_TYPE
        return "UncknownTypeNode"
