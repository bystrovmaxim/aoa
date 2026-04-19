# src/action_machine/intents/domain/__init__.py
"""
Entity intent package — ``@entity`` marker, decorator, graph inspector.

``EntityNode`` is in :mod:`action_machine.intents.domain.entity_node` and re-exported from
:mod:`action_machine.domain` to avoid a cycle with :mod:`action_machine.domain.entity`
(``BaseEntity`` ↔ ``EntityIntent``). ``DomainNode`` is interchange for ``BaseDomain`` markers.
"""

from __future__ import annotations

from action_machine.intents.domain.domain_node import DomainNode
from action_machine.intents.domain.entity_decorator import entity
from action_machine.intents.domain.entity_intent import EntityIntent, entity_info_is_set
from action_machine.intents.domain.entity_intent_inspector import EntityIntentInspector

__all__ = [
    "DomainNode",
    "EntityIntent",
    "EntityIntentInspector",
    "entity",
    "entity_info_is_set",
]
