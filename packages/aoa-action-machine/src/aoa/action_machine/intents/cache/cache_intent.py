# packages/aoa-action-machine/src/aoa/action_machine/intents/cache/cache_intent.py
"""
CacheIntent — the marker that says an operation may declare what it caches.

A marker only, as ``AccessDecideIntent``: the four cache declarations are part of
what an action is, not methods it happens to have. The decorators declare them, the
resolver finds them.
"""

from __future__ import annotations

from aoa.action_machine.intents.base_intent import BaseIntent


class CacheIntent(BaseIntent):
    """
    AI-CORE-BEGIN
        ROLE: Declaration marker for an operation's cache declarations.
        CONTRACT: Pure marker; the declarations are ``@cache_key``, ``@cache_read``, ``@cache_write`` and ``@cache_invalidate``, and declaring none is legitimate — such an operation caches nothing.
        INVARIANTS: Carries no behaviour and no state.
    AI-CORE-END
    """
