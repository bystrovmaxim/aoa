# packages/aoa-action-machine/src/aoa/action_machine/runtime/cache_entity.py
"""
CachedEntity — the namespace of entity entries, and the shape of a collection entry.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

With ``layout=CacheLayout.ENTITIES`` (issue #413) every entity of a Result is stored
once, under the key the action's ``@cache_entity_key`` builds. Those entries live under
one namespace, ``CachedEntity``, not under the action's class, so two actions that
build the same key share one entry. The entry for the call — the collection entry —
lives under the action and keeps the keys of its entities and the Result's other
fields, as JSON::

    {"fields": {"total_count": 2},
     "entities": {"orders": ["a:order:o1:row", "a:order:o2:row"], "owner": null}}

A field holding one entity keeps one key, a list keeps a list, an empty optional keeps
``null``.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = ["CachedEntity", "collection_keys", "collection_payload"]


class CachedEntity:
    """
    AI-CORE-BEGIN
    ROLE: The store namespace of entity entries, shared by every action.
    CONTRACT: Never instantiated; passed to the store in place of an action class.
    AI-CORE-END
    """


def collection_payload(fields: dict[str, Any], entities: dict[str, Any]) -> bytes:
    """The collection entry: the Result's other fields in JSON form, and the keys of its entities."""
    return json.dumps({"fields": fields, "entities": entities}, separators=(",", ":")).encode()


def collection_keys(entities: dict[str, Any]) -> list[str]:
    """Every entity key a collection entry lists, in field order, a list's keys in its order."""
    keys: list[str] = []
    for reference in entities.values():
        if isinstance(reference, list):
            keys.extend(reference)
        elif reference is not None:
            keys.append(reference)
    return keys
