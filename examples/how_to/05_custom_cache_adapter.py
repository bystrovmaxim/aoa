"""
05_custom_cache_adapter.py — Write your own cache adapter

Caching in AOA has two sides:

  - POLICY lives on the Action (override three hooks):
      cache_key(params)              -> str | None   # None = skip cache for this call
      read_cache(params, entry)      -> R | None      # interpret a stored entry; None = stale
      on_cache_write(result, params, duration_ms) -> bool   # whether to store this result

  - STORAGE lives in a coordinator injected on the machine. The shipped
    `CacheCoordinator` is in-memory; to back the cache with Redis/Memcached/etc.
    you write your own. The machine talks to it through a small duck-typed
    contract (no base class to subclass) — exactly three async methods are
    called during a run:

      async get_entry(action_cls, user_key) -> CacheEntry | None
      async invalidate(action_cls, user_key) -> bool
      async put(action_cls, user_key, result, pipeline_duration_ms) -> None

Keys MUST be namespaced per action class (module.qualname) so two actions with
the same short name never collide. Here the "backend" is a plain dict standing
in for Redis — enough to prove the contract end-to-end, in process.

Wire it: `ActionProductMachine(cache_coordinator=DictCacheAdapter())`.

How-to: ../../docs/how-to/authoring-cache-adapter_draft.md

Run:
    uv run python examples/how_to/05_custom_cache_adapter.py
"""

import asyncio
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


# ── The cache adapter: a stand-in for Redis (plain dict, namespaced) ─────────
class DictCacheAdapter:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}

    @staticmethod
    def _key(action_cls: type, user_key: str) -> str:
        return f"{action_cls.__module__}.{action_cls.__qualname__}:{user_key}"  # namespacing

    async def get_entry(self, action_cls: type, user_key: str) -> CacheEntry | None:
        return self._store.get(self._key(action_cls, user_key))

    async def put(self, action_cls: type, user_key: str, result: Any, pipeline_duration_ms: float) -> None:
        self._store[self._key(action_cls, user_key)] = CacheEntry(
            result=result, pipeline_duration_ms=pipeline_duration_ms,
        )

    async def invalidate(self, action_cls: type, user_key: str) -> bool:
        return self._store.pop(self._key(action_cls, user_key), None) is not None

    @property
    def size(self) -> int:
        return len(self._store)


# ── A normal Action that opts into caching via the three hooks ───────────────
EXECUTIONS: list[str] = []        # records every real pipeline run (proves hits skip work)


class PricingDomain(BaseDomain):
    name = "pricing"
    description = "Pricing domain"


class QuoteParams(BaseParams):
    sku: str = Field(description="Product SKU")


class QuoteResult(BaseResult):
    price: float = Field(description="Computed price")


@meta(description="Compute a price quote", domain=PricingDomain)
@check_roles(GuestRole)
class QuoteAction(BaseAction[QuoteParams, QuoteResult]):
    def cache_key(self, params: QuoteParams) -> str | None:
        return params.sku                       # cache per SKU

    async def on_cache_write(self, result, params, duration_ms) -> bool:
        return True                             # store every clean result

    @summary_aspect("Expensive pricing")
    async def quote_summary(self, params, state, box, connections):
        EXECUTIONS.append(params.sku)           # the "expensive" work
        return QuoteResult(price=len(params.sku) * 10.0)


async def main() -> None:
    cache = DictCacheAdapter()
    machine = ActionProductMachine(cache_coordinator=cache)

    async def quote(sku: str) -> float:
        result = await machine.run(Context(), QuoteAction(), QuoteParams(sku=sku), {})
        return result.price

    print("quote('ABC') ->", await quote("ABC"))   # miss -> runs pipeline
    print("quote('ABC') ->", await quote("ABC"))   # hit  -> served from adapter, no run
    print("quote('XYZW') ->", await quote("XYZW"))  # miss -> runs pipeline

    print("pipeline executions:", EXECUTIONS)       # ['ABC', 'XYZW'] — second 'ABC' was a hit
    print("cache size:", cache.size)


if __name__ == "__main__":
    asyncio.run(main())
