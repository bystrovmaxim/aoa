# src/action_machine/model/graph_model/edges/connection_graph_edge.py
"""
ConnectionGraphEdge — ASSOCIATION for ``@connection`` from Action → resource/action target.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~action_machine.model.graph_model.action_graph_node.ActionGraphNode._get_connection`:
``edge_name`` ``@connection``, ``is_dag=True``, ``properties[\"key\"]`` holds the slot key.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@connection[key]──►  Resource | Action | …
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.connection.connection_intent_resolver import (
    ConnectionIntentResolver,
)
from action_machine.model.base_action import BaseAction
from action_machine.resources.base_resource import BaseResource
from action_machine.resources.graph_model.resource_graph_node import ResourceGraphNode
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
        source_node_type: str,
        source_node: BaseGraphNode[Any],
        target_node_id: str,
        target_node_type: str,
        connection_key: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="@connection",
            is_dag=True,
            source_node_id=source_node_id,
            source_node_type=source_node_type,
            source_node=source_node,
            target_node_id=target_node_id,
            target_node_type=target_node_type,
            target_node=target_node,
            properties={"key": connection_key},
        )

    @staticmethod
    def edges_from_connections(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[ConnectionGraphEdge]:
        """Return one typed edge per ``@connection`` declaration on ``action_cls``."""
        return [
            ConnectionGraphEdge(
                source_node_id=source_node.node_id,
                source_node_type=source_node.node_type,
                source_node=source_node,
                target_node_id=TypeIntrospection.full_qualname(connection_type),
                target_node_type=ConnectionGraphEdge._resolve_target_node_type(
                    source_node,
                    connection_type,
                ),
                target_node=None,
                connection_key=connection_key,
            )
            for connection_type, connection_key in ConnectionIntentResolver.resolve_connection_types_and_keys(
                action_cls,
            )
        ]

    @staticmethod
    def _resolve_target_node_type(source_node: BaseGraphNode[Any], target_cls: type) -> str:
        """Interchange ``target_node_type`` for an associated connection target."""
        if issubclass(target_cls, BaseAction):
            return source_node.node_type
        if issubclass(target_cls, BaseResource):
            return ResourceGraphNode.NODE_TYPE
        return "UncknownTypeNode"
