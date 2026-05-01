# src/action_machine/graph_model/edges/domain_graph_edge.py
"""
DomainGraphEdge — ASSOCIATION from host class → declared domain interchange node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralize ``edge_name=\"domain\"`` plus fixed DAG semantics for edges whose
target is :class:`~action_machine.graph_model.nodes.domain_graph_node.DomainGraphNode` (``NODE_TYPE`` ``\"Domain\"``).
Requires explicit ``domain_cls`` in the constructor; factories :meth:`from_meta_declared_host` /
:meth:`from_entity_declared_host` resolve it from ``@meta`` / ``@entity`` scratch.
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_node import BaseGraphNode


class DomainGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge ``host → domain``.
    CONTRACT: ``edge_name`` ``domain``; ``target_node`` is wired by the coordinator when the domain vertex is present in the graph.
    INVARIANTS: Frozen via ``AssociationGraphEdge`` base; ``target_node`` resolves lazily elsewhere (``None`` stub).
    FAILURES:
        :exc:`~action_machine.exceptions.MissingMetaError` from :meth:`from_meta_declared_host` when meta resolution fails;
        :exc:`~action_machine.exceptions.MissingEntityInfoError` from :meth:`from_entity_declared_host` when ``@entity`` omits domain.
    AI-CORE-END
    """

    def __init__(
        self,
        source_cls: type,
        source_node: BaseGraphNode[Any],
        domain_cls: type,
    ) -> None:
        super().__init__(
            edge_name="domain",
            is_dag=True,
            source_node_id=TypeIntrospection.full_qualname(source_cls),
            source_node=source_node,
            target_node_id=TypeIntrospection.full_qualname(domain_cls),
            target_node=None,
        )

    @classmethod
    def from_meta_declared_host(
        cls,
        source_cls: type,
        source_node: BaseGraphNode[Any],
    ) -> DomainGraphEdge:
        """Materialize using :meth:`MetaIntentResolver.resolve_domain_type` (``@meta`` ``domain``)."""
        return cls(
            source_cls,
            source_node,
            MetaIntentResolver.resolve_domain_type(source_cls),
        )

    @classmethod
    def from_entity_declared_host(
        cls,
        source_cls: type,
        source_node: BaseGraphNode[Any],
    ) -> DomainGraphEdge:
        """Materialize using :meth:`EntityIntentResolver.resolve_domain_type` (``@entity`` ``domain``)."""
        return cls(
            source_cls,
            source_node,
            EntityIntentResolver.resolve_domain_type(source_cls),
        )
