# src/action_machine/domain/domain_graph_node_inspector.py
"""
DomainGraphNodeInspector — graph-node contributor for ``BaseDomain`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseDomain`` subclass tree and emits one :class:`DomainGraphNode` per
visited concrete domain class. The abstract ``BaseDomain`` axis yields no node (``DomainGraphNode`` requires ``name`` / ``description``); strict subclasses are visited in deterministic order.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseDomain  (root)  ->  ``[]`` (abstract axis)
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
    CONTRACT: Root axis ``BaseDomain`` from ``BaseGraphNodeInspector[BaseDomain]``; one node per strict subclass with a valid ``DomainGraphNode`` shape (root axis skipped).
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        # ``BaseDomain`` is abstract and has no ``name`` / ``description``; :class:`DomainGraphNode` requires them.
        if cls is BaseDomain:
            return []
        if isinstance(cls, type) and issubclass(cls, BaseDomain):
            return [DomainGraphNode(cls)]
        return []
