# src/action_machine/domain/graph_model/edges/domain_graph_edge.py
"""
DomainGraphEdge — ASSOCIATION from host class → declared domain interchange node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralize ``edge_name=\"domain\"`` plus fixed DAG semantics for edges whose
target is :class:`~action_machine.domain.graph_model.domain_graph_node.DomainGraphNode`.
Resolves declared domain via :meth:`~action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_domain_type` on ``source_cls``.
"""

from __future__ import annotations

from typing import Any

from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.exceptions import DomainGraphEdgeResolutionError
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode


class DomainGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge ``host → domain``.
    CONTRACT: ``edge_name`` ``domain``, ``target_node_type`` matches ``DomainGraphNode.NODE_TYPE``; domain from ``resolve_domain_type(source_cls)``.
    INVARIANTS: Frozen via ``AssociationGraphEdge`` base; ``target_node`` resolves lazily elsewhere (``None`` stub).
    FAILURES: :exc:`~action_machine.exceptions.DomainGraphEdgeResolutionError` when ``resolve_domain_type`` returns ``None``.
    AI-CORE-END
    """

    def __init__(
        self,
        source_cls: type,
        source_node_type: str,
        source_node: BaseGraphNode[Any],
    ) -> None:
        domain_cls = MetaIntentResolver.resolve_domain_type(source_cls)
        if domain_cls is None:
            qn = TypeIntrospection.full_qualname(source_cls)
            raise DomainGraphEdgeResolutionError(qn)
        super().__init__(
            edge_name="domain",
            is_dag=True,
            source_node_id=TypeIntrospection.full_qualname(source_cls),
            source_node_type=source_node_type,
            source_node=source_node,
            target_node_id=TypeIntrospection.full_qualname(domain_cls),
            target_node_type=DomainGraphNode.NODE_TYPE,
            target_node=None,
        )
