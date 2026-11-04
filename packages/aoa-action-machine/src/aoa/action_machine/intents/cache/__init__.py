# packages/aoa-action-machine/src/aoa/action_machine/intents/cache/__init__.py
"""
Cache — what an operation caches, declared like its object check.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Four declarations, each an ``async`` method with a description, a suffix and a fixed
signature: ``@cache_key`` (the key of a call), ``@cache_read`` (the read of a hit),
``@cache_write`` (the tags to store a clean run under) and ``@cache_invalidate`` (the
tags to drop after a clean run). At most one of each kind per operation, never
inherited; an operation that declares none caches nothing.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.intents.cache import cache_key, cache_write

    class GetOrderAction(BaseAction[GetOrderParams, GetOrderResult]):
        @cache_key("Order by id")
        async def order_cache_key(self, params: GetOrderParams, box: ToolsBox,
                                  connections: Connections) -> str | None:
            return f"order:{params.order_id}"
"""

from __future__ import annotations

from aoa.action_machine.intents.cache.cache_decorators import (
    cache_entity_key,
    cache_invalidate,
    cache_key,
    cache_read,
    cache_write,
)
from aoa.action_machine.intents.cache.cache_intent import CacheIntent
from aoa.action_machine.intents.cache.cache_intent_resolver import CacheDeclarations, CacheIntentResolver
from aoa.action_machine.intents.cache.cache_layout import CacheLayout

__all__ = [
    "CacheDeclarations",
    "CacheIntent",
    "CacheIntentResolver",
    "CacheLayout",
    "cache_entity_key",
    "cache_invalidate",
    "cache_key",
    "cache_read",
    "cache_write",
]
