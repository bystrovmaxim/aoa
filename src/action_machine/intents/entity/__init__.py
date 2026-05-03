# src/action_machine/intents/entity/__init__.py
"""
Entity intent package — ``@entity`` marker, decorator, and graph resolvers.
"""

from __future__ import annotations

from action_machine.intents.entity.entity_decorator import entity, entity_info_dict
from action_machine.intents.entity.entity_intent import EntityIntent, entity_info_is_set
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from action_machine.intents.entity.entity_relation_intent_resolver import EntityRelationIntentResolver
from action_machine.intents.entity.lifecycle_intent_resolver import (
    LifeCycleFieldResolution,
    LifeCycleFiniteAutomaton,
    LifeCycleIntentResolver,
)

__all__ = [
    "EntityIntent",
    "EntityIntentResolver",
    "EntityRelationIntentResolver",
    "LifeCycleFieldResolution",
    "LifeCycleFiniteAutomaton",
    "LifeCycleIntentResolver",
    "entity",
    "entity_info_dict",
    "entity_info_is_set",
]
