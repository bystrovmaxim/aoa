# src/action_machine/graph_model/inspectors/domain_graph_node_inspector.py
"""
DomainGraphNodeInspector — graph-node contributor for ``BaseDomain`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseDomain`` strict subclass tree and emits one :class:`DomainGraphNode` per
subtype that participates in interchange; classes opt out with
:class:`~graph.exclude_graph_model.exclude_graph_model` (see :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes`).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseDomain  (axis root — skipped when decorated with ``exclude_graph_model``)
              │
              v
    each strict subclass ``cls``  ->  ``[DomainGraphNode(cls)]`` when ``issubclass(cls, BaseDomain)``
"""

from __future__ import annotations

from typing import Any

from action_machine.domain.base_domain import BaseDomain
from action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class DomainGraphNodeInspector(BaseGraphNodeInspector[BaseDomain]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``DomainGraphNode`` rows for every loaded ``BaseDomain`` subclass.
    CONTRACT: Root axis ``BaseDomain`` from ``BaseGraphNodeInspector[BaseDomain]``; one node per visited domain class.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return DomainGraphNode(cls)
