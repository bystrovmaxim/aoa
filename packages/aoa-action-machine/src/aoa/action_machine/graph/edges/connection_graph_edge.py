# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/connection_graph_edge.py
"""
ConnectionGraphEdge — ASSOCIATION for ``@connection`` from Action → resource/action target.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror :meth:`~aoa.action_machine.graph.nodes.action_graph_node.ActionGraphNode._get_connection`:
``edge_name`` ``@connection``, ``is_dag=True``, ``properties[\"key\"]`` holds the slot key.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@connection[key]──►  Resource | Action | …
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.intents.connection.connection_intent_resolver import ConnectionIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class ConnectionGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge for ``@connection`` slots on an Action host.
    CONTRACT: ``edge_name`` ``@connection``, ``is_dag`` True; ``properties`` include ``key``; coordinator wires ``target_node``.
    INVARIANTS: Frozen via ``AssociationGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        target_node_id: str,
        connection_key: str,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="@connection",
            is_dag=True,
            target_node_id=target_node_id,
            target_node=target_node,
            properties={"key": connection_key},
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {
                "key": str(self.properties["key"]),
            },
        }

    @staticmethod
    def get_connection_edges(
        action_cls: type[Any],
    ) -> list[ConnectionGraphEdge]:
        """Return one typed edge per ``@connection`` declaration on ``action_cls``."""
        return [
            ConnectionGraphEdge(
                target_node_id=TypeIntrospection.full_qualname(connection_type),
                target_node=None,
                connection_key=connection_key,
            )
            for connection_type, connection_key in ConnectionIntentResolver.resolve_connection_types_and_keys(
                action_cls,
            )
        ]
