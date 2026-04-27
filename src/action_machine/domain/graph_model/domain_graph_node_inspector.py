# src/action_machine/domain/graph_model/domain_graph_node_inspector.py
"""
DomainGraphNodeInspector — graph-node contributor for ``BaseDomain`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseDomain`` subclass tree and emits one :class:`DomainGraphNode` per
visited domain class.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseDomain  (root axis)
              │
              v
    each strict subclass ``cls``  ->  ``[DomainGraphNode(cls)]`` when ``issubclass(cls, BaseDomain)``
"""

from __future__ import annotations

from typing import Any

from action_machine.domain.base_domain import BaseDomain
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from .domain_graph_node import DomainGraphNode


class DomainGraphNodeInspector(BaseGraphNodeInspector[BaseDomain]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``DomainGraphNode`` rows for every loaded ``BaseDomain`` subclass.
    CONTRACT: Root axis ``BaseDomain`` from ``BaseGraphNodeInspector[BaseDomain]``; one node per visited domain class.
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseDomain):
            return [DomainGraphNode(cls)]
        return []
