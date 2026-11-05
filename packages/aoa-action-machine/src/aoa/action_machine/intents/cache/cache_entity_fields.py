# packages/aoa-action-machine/src/aoa/action_machine/intents/cache/cache_entity_fields.py
"""
The entity fields of a Result, and the entity types an action's cache write stores.

A field is an entity field when its annotation is an entity class, bare, ``X | None``
or ``list[X]``: that is what ``CacheLayout.ENTITIES`` stores entity by entity. The
graph and the dead-tag check both count, as the types a write caches, its declared
tags and, in that layout, these entity types.
"""

from __future__ import annotations

import types
import typing
from typing import Any

from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import ActionSchemaIntentResolver
from aoa.action_machine.intents.cache.cache_intent_resolver import CacheIntentResolver, layout_of, tags_of
from aoa.action_machine.intents.cache.cache_layout import CacheLayout

__all__ = ["cached_types", "entity_fields", "is_entity_class"]


def is_entity_class(candidate: Any) -> bool:
    """An entity class: what ``@entity`` declared."""
    return isinstance(candidate, type) and getattr(candidate, "_entity_info", None) is not None


def _entity_of(annotation: Any) -> tuple[type, bool] | None:
    """``(entity class, is a list)`` when ``annotation`` is an entity, ``X | None`` or ``list[X]``."""
    if is_entity_class(annotation):
        return annotation, False
    origin, args = typing.get_origin(annotation), typing.get_args(annotation)
    if origin is list and len(args) == 1 and is_entity_class(args[0]):
        return args[0], True
    if isinstance(annotation, types.UnionType) or origin is typing.Union:
        members = [arg for arg in args if arg is not None.__class__]
        if len(members) == 1 and len(args) == 2:
            return _entity_of(members[0])
    return None


def entity_fields(result_type: type) -> dict[str, tuple[type, bool]]:
    """Each field of ``result_type`` typed by an entity, with its entity class and whether it holds a list."""
    found: dict[str, tuple[type, bool]] = {}
    for name, field in getattr(result_type, "model_fields", {}).items():
        entity = _entity_of(field.annotation)
        if entity is not None:
            found[name] = entity
    return found


def cached_types(action_cls: type[Any]) -> tuple[type, ...]:
    """The entity types an action's write caches: its tags, then, entity by entity, the Result's entity types."""
    write = CacheIntentResolver.declarations(action_cls).write
    if write is None:
        return ()
    found = list(tags_of(write))
    if layout_of(write) is CacheLayout.ENTITIES:
        result_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
        for entity_cls, _many in entity_fields(result_type).values():
            if entity_cls not in found:
                found.append(entity_cls)
    return tuple(found)
