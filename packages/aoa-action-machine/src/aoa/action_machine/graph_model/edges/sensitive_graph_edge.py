# packages/aoa-action-machine/src/aoa/action_machine/graph_model/edges/sensitive_graph_edge.py
"""
SensitiveGraphEdge — COMPOSITION from schema host → Sensitive interchange graph node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Typed composition edge whose ``target_node`` is a :class:`~aoa.action_machine.graph_model.nodes.sensitive_graph_node.SensitiveGraphNode`
(one ``@sensitive`` property on a params/result schema or other host type). Coordinators and
inspectors can emit this edge once wiring exists.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Params / Result / host row  ──{sensitive}──►  SensitiveGraphNode

``get_sensitive_edge(host_cls, property_name)`` returns an optional stub for one property.
``get_sensitive_edges(host_cls)`` builds one edge per resolved ``@sensitive`` property (stable sort by name).
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph_model.nodes.sensitive_graph_node import SensitiveGraphNode, SensitiveGraphNodeEdgeInfo
from aoa.action_machine.intents.sensitive.sensitive_intent_resolver import SensitiveIntentResolver
from aoa.graph.composition_graph_edge import CompositionGraphEdge


class SensitiveGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge schema or declaration host → sensitive masking graph node.
    CONTRACT: ``edge_name`` literal ``sensitive``; ``is_dag`` False; pass wired ``sensitive_node`` or stub ``target_node_id``;
        :meth:`get_sensitive_edge` builds an optional stub for one property;
        :meth:`get_sensitive_edges` builds edges from :meth:`~aoa.action_machine.intents.sensitive.sensitive_intent_resolver.SensitiveIntentResolver.resolve_sensitive_all_fields`.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        sensitive_node: SensitiveGraphNode | None = None,
        target_node_id: str | None = None,
    ) -> None:
        if (sensitive_node is None) == (target_node_id is None):
            msg = "SensitiveGraphEdge requires exactly one of sensitive_node or target_node_id"
            raise TypeError(msg)
        if sensitive_node is not None:
            super().__init__(
                edge_name="sensitive",
                is_dag=False,
                target_node_id=sensitive_node.node_id,
                target_node=sensitive_node,
            )
        else:
            tid = target_node_id
            assert tid is not None
            super().__init__(
                edge_name="sensitive",
                is_dag=False,
                target_node_id=tid,
                target_node=None,
            )

    @staticmethod
    def get_sensitive_edge(host_cls: type, property_name: str) -> SensitiveGraphEdge | None:
        """Return a stub composition edge toward :class:`SensitiveGraphNode` when ``property_name`` is ``@sensitive`` on ``host_cls``."""
        if SensitiveIntentResolver.resolve_sensitive_field(host_cls, property_name) is None:
            return None
        tid = SensitiveGraphNodeEdgeInfo.for_property(host_cls, property_name).target_node_id
        return SensitiveGraphEdge(target_node_id=tid)

    @staticmethod
    def get_all_sensitive_edges(host_cls: type[Any]) -> list[SensitiveGraphEdge]:
        """Return one composition edge per public member with ``@sensitive`` on ``host_cls``."""
        rows = SensitiveIntentResolver.resolve_sensitive_all_fields(host_cls)
        out: list[SensitiveGraphEdge] = []
        for property_name in sorted(rows):
            node = SensitiveGraphNode(host_cls, property_name)
            out.append(SensitiveGraphEdge(sensitive_node=node))
        return out
