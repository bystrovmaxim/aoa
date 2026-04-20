# src/action_machine/domain/entity_graph_node_inspector.py
"""
EntityGraphNodeInspector — graph-node contributor for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded ``BaseEntity`` subclass tree and emits one :class:`EntityGraphNode` per
visited class (including the ``BaseEntity`` axis when :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes` calls the root).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseEntity  (root)  ->  ``[EntityGraphNode(BaseEntity)]`` when included in the walk
              │
              v
    each loaded subclass ``cls``  ->  ``[EntityGraphNode(cls)]`` when ``issubclass(cls, BaseEntity)``
"""

from __future__ import annotations

from typing import Any

from action_machine.domain.entity import BaseEntity
from action_machine.domain.entity_graph_node import EntityGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector


class EntityGraphNodeInspector(BaseGraphNodeInspector[BaseEntity]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``EntityGraphNode`` rows for every loaded ``BaseEntity`` subclass.
    CONTRACT: Root axis ``BaseEntity`` from ``BaseGraphNodeInspector[BaseEntity]``; one node per visited subtype.
    AI-CORE-END
    """

    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        if isinstance(cls, type) and issubclass(cls, BaseEntity):
            return [EntityGraphNode(cls)]
        return []
