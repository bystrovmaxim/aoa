# src/action_machine/intents/entity/__init__.py
"""
Entity intent package — ``@entity`` marker, decorator, graph inspector.

``EntityGraphNode`` lives in :mod:`action_machine.domain.entity_graph_node` and is
re-exported from :mod:`action_machine.domain` to avoid a cycle with
:mod:`action_machine.domain.entity` (``BaseEntity`` ↔ ``EntityIntent``).
``DomainGraphNode`` is interchange for ``BaseDomain`` markers
(:mod:`action_machine.domain.domain_graph_node`).
"""

from __future__ import annotations

from action_machine.domain.domain_graph_node import DomainGraphNode
from action_machine.intents.entity.entity_decorator import entity
from action_machine.legacy.entity_intent import EntityIntent, entity_info_is_set
from action_machine.legacy.entity_intent_inspector import EntityIntentInspector

__all__ = [
    "DomainGraphNode",
    "EntityIntent",
    "EntityIntentInspector",
    "entity",
    "entity_info_is_set",
]
