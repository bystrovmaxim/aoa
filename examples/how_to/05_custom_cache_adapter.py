"""
05_custom_cache_adapter.py — Write your own cache adapter

Caching in AOA has two sides:

  - POLICY lives on the Action (override four hooks):
      cache_key(params)                              -> str | None
      read_cache(params, entry)                      -> R | None
      on_cache_write(result, params, duration_ms)    -> list[CacheTag] | None
      on_cache_invalidate(params, result)            -> list[CacheTag] | None

  - STORAGE lives in a coordinator injected on the machine. The shipped
    `CacheCoordinator` is in-memory; to back the cache with Redis/Memcached/etc.
    you write your own. The machine talks to it through a duck-typed contract
    (no base class to subclass) — four async methods are called during a run:

      async get_entry(action_cls, user_key)  -> CacheEntry | None
      async invalidate(action_cls, user_key) -> bool
      async put(action_cls, user_key, result, pipeline_duration_ms,
                tags: list[CacheTag] | None = None) -> None
      async evict_by_tags(directive_tags: frozenset[CacheTag]) -> int

    `evict_by_tags` receives a frozenset of CacheTag matchers; it must evict
    every entry whose stored tags match any directive (wildcard: None field =
    match any value). Returns the number of entries removed.

Keys MUST be namespaced per action class (module.qualname) so two actions with
the same short name never collide.

How-to: ../../docs/how-to/authoring-cache-adapter.md

Run:
    uv run python examples/how_to/05_custom_cache_adapter.py
"""

import asyncio
from collections import defaultdict
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag

# ── The cache adapter: a stand-in for Redis (plain dict, namespaced) ─────────

class DictCacheAdapter:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._tag_to_keys: defaultdict[CacheTag, set[str]] = defaultdict(set)
        self._key_to_tags: dict[str, set[CacheTag]] = {}

    @staticmethod
    def _key(action_cls: type, user_key: str) -> str:
        return f"{action_cls.__module__}.{action_cls.__qualname__}:{user_key}"

    async def get_entry(self, action_cls: type, user_key: str) -> CacheEntry | None:
        return self._store.get(self._key(action_cls, user_key))

    async def put(
        self,
        action_cls: type,
        user_key: str,
        result: Any,
        pipeline_duration_ms: float,
        tags: list[CacheTag] | None = None,
    ) -> None:
        k = self._key(action_cls, user_key)
        self._store[k] = CacheEntry(result=result, pipeline_duration_ms=pipeline_duration_ms)
        if tags:
            self._key_to_tags[k] = set(tags)
            for tag in tags:
                self._tag_to_keys[tag].add(k)

    async def invalidate(self, action_cls: type, user_key: str) -> bool:
        k = self._key(action_cls, user_key)
        if k not in self._store:
            return False
        del self._store[k]
        for tag in self._key_to_tags.pop(k, set()):
            self._tag_to_keys[tag].discard(k)
        return True

    async def evict_by_tags(self, directive_tags: frozenset[CacheTag]) -> int:
        # Wildcard matching: CacheTag(type=T) matches stored tags with any key.
        candidates: set[str] = set()
        for stored_tag, keys in list(self._tag_to_keys.items()):
            for d in directive_tags:
                type_ok = d.type is None or d.type is stored_tag.type
                key_ok = d.key is None or d.key == stored_tag.key
                if type_ok and key_ok:
                    candidates.update(keys)
                    break
        for k in candidates:
            del self._store[k]
            for tag in self._key_to_tags.pop(k, set()):
                self._tag_to_keys[tag].discard(k)
        return len(candidates)

    @property
    def size(self) -> int:
        return len(self._store)


# ── Domain and action types used as CacheTag.type ────────────────────────────

class PricingDomain(BaseDomain):
    name = "pricing"
    description = "Pricing domain"


class Quote:
    """Sentinel type for CacheTag(type=Quote, key=sku)."""


# ── A normal Action that opts into caching ────────────────────────────────────

EXECUTIONS: list[str] = []  # records every real pipeline run (proves hits skip work)


class QuoteParams(BaseParams):
    sku: str = Field(description="Product SKU")


class QuoteResult(BaseResult):
    price: float = Field(description="Computed price")


@meta(description="Compute a price quote", domain=PricingDomain)
@check_roles(GuestRole)
class QuoteAction(BaseAction[QuoteParams, QuoteResult]):
    def cache_key(self, params: QuoteParams) -> str | None:
        return params.sku  # cache per SKU

    async def on_cache_write(
        self, result: QuoteResult, params: QuoteParams, duration_ms: float
    ) -> list[CacheTag] | None:
        # Tag the entry so it can later be evicted by type or by sku.
        return [CacheTag(type=Quote, key=params.sku)]

    @summary_aspect("Expensive pricing")
    async def quote_summary(self, params, state, box, connections):
        EXECUTIONS.append(params.sku)  # the "expensive" work
        return QuoteResult(price=len(params.sku) * 10.0)


async def main() -> None:
    cache = DictCacheAdapter()
    machine = ActionProductMachine(cache_coordinator=cache)

    async def quote(sku: str) -> float:
        result = await machine.run(Context(), QuoteAction(), QuoteParams(sku=sku), {})
        return result.price

    print("quote('ABC') ->", await quote("ABC"))    # miss → runs pipeline
    print("quote('ABC') ->", await quote("ABC"))    # hit  → served from adapter, no run
    print("quote('XYZW') ->", await quote("XYZW"))  # miss → runs pipeline

    print("pipeline executions:", EXECUTIONS)        # ['ABC', 'XYZW'] — second 'ABC' was a hit
    print("cache size:", cache.size)


if __name__ == "__main__":
    asyncio.run(main())
