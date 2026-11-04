# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/cache_tags_validator.py
"""
CacheTagsValidator — refuse a cache invalidation with nothing to drop, and a cached type nothing drops.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

No declaration without an effect. Across every action of one graph:

- a **dead invalidation** — an entity type an ``@cache_invalidate`` names that no
  ``@cache_write`` names — drops nothing, ever;
- a **dead tag** — an entity type an ``@cache_write`` caches (its tags, and with
  ``layout=CacheLayout.ENTITIES`` the entity types its Result stores entity by entity)
  that no ``@cache_invalidate`` names — marks entries nothing will ever tell they are stale.

Both refuse the build. The check sees one graph, which is one service; it is exact
while a cache store belongs to one service. The pass only reads.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.intents.cache.cache_entity_fields import cached_types
from aoa.action_machine.intents.cache.cache_intent_resolver import CacheIntentResolver, tags_of
from aoa.action_machine.model.base_action import BaseAction

__all__ = ["CacheTagsError", "validate_cache_tags"]


class CacheTagsError(InvalidGraphError):
    """
    AI-CORE-BEGIN
    ROLE: Build refusal of a cache tag type with no counterpart in the graph.
    CONTRACT: Names the action and the entity type, and which side is missing.
    AI-CORE-END
    """


def _tagged(actions: list[type[Any]], kind: str) -> dict[type, list[str]]:
    """Each type the ``kind`` declarations of ``actions`` cache or drop, with the actions that do."""
    found: dict[type, list[str]] = {}
    for action_cls in actions:
        if kind == "write":
            types_named = cached_types(action_cls)
        else:
            method = CacheIntentResolver.declarations(action_cls).invalidate
            types_named = tags_of(method) if method is not None else ()
        for tag in types_named:
            found.setdefault(tag, []).append(action_cls.__name__)
    return found


def validate_cache_tags(nodes: Iterable[Any]) -> None:
    """Refuse a dead invalidation or a dead tag among the actions of ``nodes``."""
    actions = sorted(
        (node.node_obj for node in nodes if isinstance(node.node_obj, type) and issubclass(node.node_obj, BaseAction)),
        key=lambda cls: (cls.__module__, cls.__qualname__),
    )
    cached, dropped = _tagged(actions, "write"), _tagged(actions, "invalidate")
    for entity_type, droppers in sorted(dropped.items(), key=lambda item: item[0].__name__):
        if entity_type not in cached:
            raise CacheTagsError(f"{droppers[0]} drops {entity_type.__name__}, but no action caches it.")
    for entity_type, writers in sorted(cached.items(), key=lambda item: item[0].__name__):
        if entity_type not in dropped:
            raise CacheTagsError(
                f"{writers[0]} caches {entity_type.__name__}, but no action invalidates it; "
                "nothing will tell its entries they are stale."
            )
