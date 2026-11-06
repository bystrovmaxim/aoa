"""
05_custom_cache_adapter.py — Write your own cache adapter

Caching in AOA has two sides:

  - POLICY lives on the Action, in four declarations (each takes
    self, params, box, connections first):
      @cache_key         (...)                       -> str | None
      @cache_read        (..., entry)                -> R | None
      @cache_write       (..., result, duration_ms)  -> list[CacheTag] | None
      @cache_invalidate  (..., result)               -> list[CacheTag] | None

  - STORAGE lives in a coordinator injected on the machine. The shipped
    `CacheCoordinator` is in-memory; to back the cache with Redis/Memcached/etc.
    you write your own. The store keeps bytes: the machine hands it the
    Result's JSON in UTF-8 and reads every hit back into a new Result itself.
    It talks to the store through a duck-typed contract (no base class to
    subclass) — these async methods are called during a run:

      async get_entry(action_cls, user_key)  -> StoredCacheEntry | None
      async get_entries(action_cls, user_keys) -> list[StoredCacheEntry | None]
      async invalidate(action_cls, user_key) -> bool
      async put(action_cls, user_key, payload: bytes, pipeline_duration_ms,
                tags: list[CacheTag] | None = None) -> None
      async evict_by_tags(directive_tags: frozenset[CacheTag]) -> int

    `get_entries` reads several keys in one call (Redis `MGET`); a hit of a
    Result cached entity by entity reads all its entities through it.
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

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.cache import cache_invalidate, cache_key, cache_write
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections, InMemoryDataSource
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_entry import StoredCacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox

# ── The cache adapter: a stand-in for Redis (plain dict, namespaced) ─────────

class DictCacheAdapter:
    def __init__(self) -> None:
        self._store: dict[str, StoredCacheEntry] = {}
        self._tag_to_keys: defaultdict[CacheTag, set[str]] = defaultdict(set)
        self._key_to_tags: dict[str, set[CacheTag]] = {}

    @staticmethod
    def _key(action_cls: type, user_key: str) -> str:
        return f"{action_cls.__module__}.{action_cls.__qualname__}:{user_key}"

    async def get_entry(self, action_cls: type, user_key: str) -> StoredCacheEntry | None:
        return self._store.get(self._key(action_cls, user_key))

    async def get_entries(self, action_cls: type, user_keys: list[str]) -> list[StoredCacheEntry | None]:
        # One round trip for many keys, as Redis MGET does.
        return [self._store.get(self._key(action_cls, user_key)) for user_key in user_keys]

    async def put(
        self,
        action_cls: type,
        user_key: str,
        payload: bytes,
        pipeline_duration_ms: float,
        tags: list[CacheTag] | None = None,
    ) -> None:
        # Bytes in, bytes out: the machine encodes the Result and reads it back.
        k = self._key(action_cls, user_key)
        self._store[k] = StoredCacheEntry(payload=payload, pipeline_duration_ms=pipeline_duration_ms)
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

    def payload(self, action_cls: type, user_key: str) -> bytes:
        """What the store holds for a key — the Result's JSON, as Redis would hold it."""
        return self._store[self._key(action_cls, user_key)].payload


# ── Domain and the entity a cache tag names ──────────────────────────────────

class PricingDomain(BaseDomain):
    name = "pricing"
    description = "Pricing domain"


@meta(description="Where PricingStorage keeps its rows")
class PricingDataSource(InMemoryDataSource):
    """The store PricingStorage works with."""


@meta(description="Stores the pricing entities", domain=PricingDomain)
class PricingStorage(BaseStorage[PricingDataSource]):
    """Hold the pricing entities."""


@entity(description="A price quote", resource=PricingStorage)
class QuoteCoreEntity(BaseCoreEntity):
    """What a quote's cache entry is tagged with: CacheTag(type=QuoteCoreEntity, key=sku)."""

    id: str = Field(description="Product SKU")


# ── A normal Action that opts into caching ────────────────────────────────────

EXECUTIONS: list[str] = []  # records every real pipeline run (proves hits skip work)


class QuoteParams(BaseParams):
    sku: str = Field(description="Product SKU")


class QuoteResult(BaseResult):
    price: float = Field(description="Computed price")


@meta(description="Compute a price quote", domain=PricingDomain)
@check_roles(GuestRole)
class QuoteAction(BaseAction[QuoteParams, QuoteResult]):
    @cache_key("Quote per SKU")
    async def quote_cache_key(self, params: QuoteParams, box: ToolsBox, connections: Connections) -> str | None:
        return params.sku

    @cache_write("Keep every quote", tags=(QuoteCoreEntity,))
    async def quote_cache_write(
        self, params: QuoteParams, box: ToolsBox, connections: Connections, result: QuoteResult, duration_ms: float
    ) -> list[CacheTag] | None:
        # Tag the entry so it can later be evicted by type or by sku.
        return [CacheTag(type=QuoteCoreEntity, key=params.sku)]

    @summary_aspect("Expensive pricing")
    async def quote_summary(self, params: QuoteParams, state: BaseState, box: ToolsBox, connections: Connections) -> QuoteResult:
        EXECUTIONS.append(params.sku)  # the "expensive" work
        return QuoteResult(price=len(params.sku) * 10.0)


@meta(description="Change a price", domain=PricingDomain)
@check_roles(GuestRole)
class RepriceAction(BaseAction[QuoteParams, QuoteResult]):
    @cache_invalidate("Drop the quote of the repriced SKU", tags=(QuoteCoreEntity,))
    async def quote_cache_invalidate(
        self, params: QuoteParams, box: ToolsBox, connections: Connections, result: QuoteResult
    ) -> list[CacheTag] | None:
        return [CacheTag(type=QuoteCoreEntity, key=params.sku)]

    @summary_aspect("Store the new price")
    async def reprice_summary(self, params: QuoteParams, state: BaseState, box: ToolsBox, connections: Connections) -> QuoteResult:
        return QuoteResult(price=0.0)


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
    print("stored for 'ABC':", cache.payload(QuoteAction, "ABC"))

    await machine.run(Context(), RepriceAction(), QuoteParams(sku="ABC"), {})  # drops ABC's entry
    print("after reprice, cache size:", cache.size)
    print("quote('ABC') ->", await quote("ABC"))    # miss again → runs pipeline
    print("pipeline executions:", EXECUTIONS)


if __name__ == "__main__":
    asyncio.run(main())
