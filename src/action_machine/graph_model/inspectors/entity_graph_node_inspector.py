# src/action_machine/graph_model/inspectors/entity_graph_node_inspector.py
"""
EntityGraphNodeInspector — graph-node contributor for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded strict ``BaseEntity`` subclass tree and emits one :class:`EntityGraphNode` per
subtype that participates in interchange; classes opt out with
:class:`~graph.exclude_graph_model.exclude_graph_model` (see :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes`).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseEntity  (axis root — skipped when decorated with ``exclude_graph_model``)
              │
              v
    each loaded strict subclass ``cls``  ->  ``[EntityGraphNode(cls)]`` when ``issubclass(cls, BaseEntity)``
"""

from __future__ import annotations

from typing import Any

from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class EntityGraphNodeInspector(BaseGraphNodeInspector[BaseEntity]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``EntityGraphNode`` rows for every loaded ``BaseEntity`` subclass.
    CONTRACT: Root axis ``BaseEntity`` from ``BaseGraphNodeInspector[BaseEntity]``; one node per visited subtype.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return EntityGraphNode(cls)
