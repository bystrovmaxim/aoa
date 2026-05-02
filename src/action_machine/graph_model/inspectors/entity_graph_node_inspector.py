# src/action_machine/graph_model/inspectors/entity_graph_node_inspector.py
"""
EntityGraphNodeInspector — graph-node contributor for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded strict ``BaseEntity`` subclass tree and emits one :class:`EntityGraphNode` per
subtype that has a usable ``@entity`` declaration for graph export (description + ``domain``);
other subtypes — for example ephemeral test helpers nested under pytest methods — are **skipped**
so they cannot leave stray rows in Python’s class registry and later break interchange builds.

Classes opt out deterministically with
:class:`~graph.exclude_graph_model.exclude_graph_model`
(see :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes`).

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
from action_machine.exceptions.missing_entity_info_error import MissingEntityInfoError
from action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
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
        try:
            EntityIntentResolver.resolve_description(cls)
            EntityIntentResolver.resolve_domain_type(cls)
        except MissingEntityInfoError:
            return None
        return EntityGraphNode(cls)
