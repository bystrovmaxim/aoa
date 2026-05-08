# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/__init__.py
"""
Entity intent package — ``@entity`` marker, decorator, and graph resolvers.
"""

from __future__ import annotations

from aoa.action_machine.intents.entity.entity_decorator import entity, entity_info_dict
from aoa.action_machine.intents.entity.entity_intent import EntityIntent, entity_info_is_set
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.entity.entity_relation_intent_resolver import EntityRelationIntentResolver
from aoa.action_machine.intents.entity.lifecycle_intent_resolver import (
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
