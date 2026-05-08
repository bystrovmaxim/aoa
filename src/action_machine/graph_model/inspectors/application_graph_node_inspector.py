# src/action_machine/graph_model/inspectors/application_graph_node_inspector.py
"""
ApplicationGraphNodeInspector — graph-node contributor for :class:`~action_machine.application.application.Application`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``Application`` strict subclass tree and emits one
:class:`ApplicationGraphNode` per type; the root marker is included unless opted
out via :class:`~graph.exclude_graph_model.exclude_graph_model`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Application  (axis root)
              │
              v
    each visited ``cls``  ->  ``ApplicationGraphNode(cls)``
"""

from __future__ import annotations

from typing import Any

from action_machine.application.application import Application
from action_machine.graph_model.nodes.application_graph_node import ApplicationGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class ApplicationGraphNodeInspector(BaseGraphNodeInspector[Application]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ApplicationGraphNode`` rows for ``Application`` and its strict subclasses.
    CONTRACT: Root axis ``Application``; one node per visited class.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return ApplicationGraphNode(cls)
