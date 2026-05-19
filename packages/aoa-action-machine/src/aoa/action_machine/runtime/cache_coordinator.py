# packages/aoa-action-machine/src/aoa/action_machine/runtime/cache_coordinator.py
"""
In-memory cache store for action results, owned by :class:`ActionProductMachine`.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``CacheCoordinator`` is **opt-in**: construct ``ActionProductMachine(...,
cache_coordinator=CacheCoordinator())``. Default ``cache_coordinator=None`` means the
machine never reads or writes this store.

Keys are namespaced per action class using ``module.qualname`` so distinct classes
with the same short name do not collide. The coordinator is **not** attached via
``ClassVar`` on ``BaseAction``; one instance is injected on the machine.

**v1 does not provide single-flight:** concurrent misses for the same key may each
execute the full pipeline until entries land. Coalescing would be a separate change.

All mutating operations share one :class:`asyncio.Lock` (see class docstring).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from aoa.action_machine.runtime.cache_entry import CacheEntry


class CacheCoordinator:
    """
    In-memory cache store shared across action classes in one machine instance.

    Wired through :class:`~aoa.action_machine.runtime.action_product_machine.ActionProductMachine`
    only; actions interact via ``cache_key``, ``read_cache``, and ``on_cache_write``,
    not by calling this type directly from ``BaseAction``.

    All mutating operations are serialized with a single :class:`asyncio.Lock`.
    There is **no** TTL and **no** single-flight in v1; staleness is handled by
    returning ``None`` from ``read_cache`` so the machine invalidates and re-runs
    the pipeline.
    """

    def __init__(self, max_size: int | None = None) -> None:
        """Create an empty store; ``max_size`` caps entries and enables eviction when full."""
        self._store: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._max_size: int | None = max_size

    @staticmethod
    def _class_prefix(action_cls: type) -> str:
        """Return ``module.qualname:`` prefix for keys belonging to ``action_cls``."""
        return f"{action_cls.__module__}.{action_cls.__qualname__}:"

    @classmethod
    def _make_key(cls, action_cls: type, user_key: str) -> str:
        """Build the internal store key from class prefix and ``user_key``."""
        return f"{cls._class_prefix(action_cls)}{user_key}"

    def _evict_one(self) -> None:
        """Remove the entry with the smallest ``pipeline_duration_ms`` (capacity policy)."""
        if not self._store:
            return
        evict_key = min(
            self._store,
            key=lambda k: self._store[k].pipeline_duration_ms,
        )
        del self._store[evict_key]

    @property
    def size(self) -> int:
        """Number of entries currently stored."""
        return len(self._store)

    async def get_entry(self, action_cls: type, user_key: str) -> CacheEntry | None:
        """Return a namespaced row or ``None``; on hit, bump access metadata."""
        internal_key = self._make_key(action_cls, user_key)
        async with self._lock:
            entry = self._store.get(internal_key)
            if entry is None:
                return None
            entry.access_count += 1
            entry.last_accessed_at = time.monotonic()
            return entry

    async def put(
        self,
        action_cls: type,
        user_key: str,
        result: Any,
        pipeline_duration_ms: float,
    ) -> None:
        """Upsert ``result`` under the namespaced key; evict one row if at ``max_size``."""
        internal_key = self._make_key(action_cls, user_key)
        async with self._lock:
            if self._max_size is not None and len(self._store) >= self._max_size:
                if internal_key not in self._store:
                    self._evict_one()
            self._store[internal_key] = CacheEntry(
                result=result,
                pipeline_duration_ms=pipeline_duration_ms,
            )

    async def invalidate(self, action_cls: type, user_key: str) -> bool:
        """Delete one namespaced key; return whether a row was removed."""
        internal_key = self._make_key(action_cls, user_key)
        async with self._lock:
            if internal_key in self._store:
                del self._store[internal_key]
                return True
            return False

    async def clear(self, action_cls: type | None = None) -> int:
        """Drop all rows, or only rows for ``action_cls``; return how many were removed."""
        async with self._lock:
            if action_cls is None:
                count = len(self._store)
                self._store.clear()
                return count
            prefix = self._class_prefix(action_cls)
            keys_to_remove = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._store[k]
            return len(keys_to_remove)
