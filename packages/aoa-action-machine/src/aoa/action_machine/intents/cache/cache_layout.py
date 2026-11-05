# packages/aoa-action-machine/src/aoa/action_machine/intents/cache/cache_layout.py
"""
CacheLayout — how a cache write stores its Result: whole, or entity by entity.

``WHOLE`` (the default) keeps one entry per call with the Result's JSON. ``ENTITIES``
keeps every entity of the Result's entity fields once, under a key the action's
``@cache_entity_key`` builds, and an entry for the call that lists those keys with the
Result's other fields — a library card that lists shelf numbers, not books. Two
actions that build the same key for an entity share its entry.
"""

from __future__ import annotations

from enum import Enum


class CacheLayout(Enum):
    """
    AI-CORE-BEGIN
    ROLE: The layout ``@cache_write(..., layout=...)`` stores a Result in.
    CONTRACT: ``WHOLE`` — one entry of the Result's JSON; ``ENTITIES`` — entity entries plus a collection entry of their keys.
    AI-CORE-END
    """

    WHOLE = "whole"
    ENTITIES = "entities"
