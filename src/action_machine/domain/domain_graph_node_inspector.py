# src/action_machine/domain/domain_graph_node_inspector.py
"""
DomainGraphNodeInspector — graph-node contributor for ``BaseDomain`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseDomain`` strict subclass tree and emits one :class:`DomainGraphNode` per
visited concrete domain class. The ``BaseDomain`` axis is excluded via
:meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector._graph_node_walk_excluded_types`
(``DomainGraphNode`` expects ``name`` / ``description`` on concrete domains).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseDomain  (root axis, skipped in walk)
              │
              v
    each strict subclass ``cls``  ->  ``[DomainGraphNode(cls)]`` when ``issubclass(cls, BaseDomain)``
"""

from __future__ import annotations

from typing import Any

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.domain_graph_node import DomainGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class DomainGraphNodeInspector(BaseGraphNodeInspector[BaseDomain]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``DomainGraphNode`` rows for every loaded ``BaseDomain`` subclass.
    CONTRACT: Root axis ``BaseDomain`` from ``BaseGraphNodeInspector[BaseDomain]``; one node per strict subclass with a valid ``DomainGraphNode`` shape (root excluded via :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector._graph_node_walk_excluded_types`).
    AI-CORE-END
    """

    def _graph_node_walk_excluded_types(self) -> frozenset[type]:
        return frozenset({BaseDomain})

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseDomain):
            return [DomainGraphNode(cls)]
        return []
