# src/action_machine/graph_model/edges/connection_graph_edge.py
"""
ConnectionGraphEdge — ASSOCIATION for ``@connection`` from Action → resource/action target.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~action_machine.graph_model.nodes.action_graph_node.ActionGraphNode._get_connection`:
``edge_name`` ``@connection``, ``is_dag=True``, ``properties[\"key\"]`` holds the slot key.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@connection[key]──►  Resource | Action | …
"""

from __future__ import annotations

from typing import Any, cast

from action_machine.graph_model.nodes.resource_graph_node import ResourceGraphNode
from action_machine.intents.connection.connection_intent_resolver import (
    ConnectionIntentResolver,
)
from action_machine.model.base_action import BaseAction
from action_machine.resources.base_resource import BaseResource
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode


class ConnectionGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge for ``@connection`` slots on an Action host.
    CONTRACT: ``edge_name`` ``@connection``, ``is_dag`` True; ``properties`` include non-empty ``key`` string.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        source_node_id: str,
        source_node: BaseGraphNode[Any],
        target_node_id: str,
        connection_key: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="@connection",
            is_dag=True,
            source_node_id=source_node_id,
            source_node=source_node,
            target_node_id=target_node_id,
            target_node=target_node,
            properties={"key": connection_key},
        )

    @property
    def target_node_type(self) -> str:
        if self.target_node is not None:
            return cast(str, self.target_node.node_type)
        slot_key = self.properties.get("key")
        if not isinstance(slot_key, str):
            msg = "@connection edge requires properties['key'] to resolve stub target_vertex_type."
            raise RuntimeError(msg)

        src = self.source_node
        if src is None:
            msg = "ConnectionGraphEdge: source_node is unset."
            raise RuntimeError(msg)

        action_cls = ConnectionGraphEdge._action_cls_from_source(src)

        for connection_type, connection_key in ConnectionIntentResolver.resolve_connection_types_and_keys(
            action_cls,
        ):
            if (
                TypeIntrospection.full_qualname(connection_type) == self.target_node_id
                and connection_key == slot_key
            ):
                return ConnectionGraphEdge._resolve_target_node_type(src, connection_type)

        msg = (
            "ConnectionGraphEdge: no declaration matches "
            f"target_node_id={self.target_node_id!r} and properties['key']={slot_key!r}."
        )
        raise RuntimeError(msg)

    @staticmethod
    def get_connection_edges(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[ConnectionGraphEdge]:
        """Return one typed edge per ``@connection`` declaration on ``action_cls``."""
        return [
            ConnectionGraphEdge(
                source_node_id=source_node.node_id,
                source_node=source_node,
                target_node_id=TypeIntrospection.full_qualname(connection_type),
                target_node=None,
                connection_key=connection_key,
            )
            for connection_type, connection_key in ConnectionIntentResolver.resolve_connection_types_and_keys(
                action_cls,
            )
        ]

    @staticmethod
    def _action_cls_from_source(source_node: BaseGraphNode[Any]) -> type[Any]:
        obj = getattr(source_node, "node_obj", None)
        if isinstance(obj, type):
            return obj
        msg = (
            f"ConnectionGraphEdge: interchange source {source_node.node_id!r} "
            "expects node_obj action class."
        )
        raise TypeError(msg)

    @staticmethod
    def _resolve_target_node_type(source_node: BaseGraphNode[Any], target_cls: type) -> str:
        """Interchange ``target_node_type`` for an associated connection target."""
        if issubclass(target_cls, BaseAction):
            return source_node.node_type
        if issubclass(target_cls, BaseResource):
            return ResourceGraphNode.NODE_TYPE
        return "UncknownTypeNode"
