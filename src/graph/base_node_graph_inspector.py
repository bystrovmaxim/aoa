# src/graph/base_node_graph_inspector.py
"""
BaseNodeGraphInspector — abstract base for inspectors that feed :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``NodeGraphCoordinator`` aggregates :class:`~graph.base_graph_node.BaseGraphNode`
rows from inspector **instances**. This ABC is the typed contract for that path:
subclasses implement :meth:`get_graph_nodes` only (no ``GraphCoordinator`` classmethod
API).

Inspectors that also participate in the main facet graph typically inherit both
:class:`~graph.base_intent_inspector.BaseIntentInspector` and ``BaseNodeGraphInspector``.
:class:`~graph.base_inspector.BaseInspector` remains the minimal hook type for other
call sites; this class is the **typed** contract for :class:`~graph.node_graph_coordinator.NodeGraphCoordinator` only.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseNodeGraphInspector subclass instance
              │
              v
    get_graph_nodes()  ->  list[BaseGraphNode[Any]]
              │
              v
    NodeGraphCoordinator.build([...])
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from graph.base_graph_node import BaseGraphNode


class BaseNodeGraphInspector(ABC):
    """
    AI-CORE-BEGIN
    ROLE: Abstract contract for interchange-node emission into ``NodeGraphCoordinator``.
    CONTRACT: Concrete subclasses implement :meth:`get_graph_nodes` on instances.
    INVARIANTS: Cannot be instantiated directly; not registered with ``GraphCoordinator`` by itself.
    AI-CORE-END
    """

    @abstractmethod
    def get_graph_nodes(self) -> list[BaseGraphNode[Any]]:
        """
        Return all :class:`~graph.base_graph_node.BaseGraphNode` rows this inspector contributes.

        Order is preserved when the coordinator concatenates multiple inspectors.
        """
