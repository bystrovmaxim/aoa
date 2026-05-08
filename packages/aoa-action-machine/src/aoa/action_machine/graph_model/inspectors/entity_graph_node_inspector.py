# packages/aoa-action-machine/src/aoa/action_machine/graph_model/inspectors/entity_graph_node_inspector.py
"""
EntityGraphNodeInspector — graph-node contributor for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded strict ``BaseEntity`` subclass tree and emits one :class:`EntityGraphNode` per
participating subtype. Classes opt out deterministically with
:class:`~aoa.graph.exclude_graph_model.exclude_graph_model`
(see :meth:`~aoa.graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes`).

``@entity`` declaration errors are resolved by the entity decorator / intent layer and
surface when the application initializes the graph, not as pre-checks in this inspector.

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

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.base_graph_node_inspector import BaseGraphNodeInspector


class EntityGraphNodeInspector(BaseGraphNodeInspector[BaseEntity]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``EntityGraphNode`` rows for every loaded ``BaseEntity`` subclass.
    CONTRACT: Root axis ``BaseEntity`` from ``BaseGraphNodeInspector[BaseEntity]``; one ``EntityGraphNode`` per visited subtype after ``exclude_graph_model`` filtering.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return EntityGraphNode(cls)
