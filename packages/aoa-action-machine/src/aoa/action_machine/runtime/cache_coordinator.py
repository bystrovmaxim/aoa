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

**Tag index.** ``put`` accepts a ``tags: list[CacheTag]`` list; two reverse-lookup
dicts are kept in sync — ``_tag_to_keys`` (CacheTag → internal keys) and
``_key_to_tags`` (internal key → CacheTag set). ``evict_by_tags`` uses wildcard
matching: ``CacheTag(type=T)`` (no key) matches every stored tag whose type is T;
``CacheTag(key=K)`` (no type) matches every stored tag whose key is K.

**v1 does not provide single-flight:** concurrent misses for the same key may each
execute the full pipeline until entries land. Coalescing would be a separate change.

All mutating operations share one :class:`asyncio.Lock`.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any

from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag


class CacheCoordinator:
    """
    In-memory cache store shared across action classes in one machine instance.

    Wired through :class:`~aoa.action_machine.runtime.action_product_machine.ActionProductMachine`
    only; actions interact via ``cache_key``, ``read_cache``, ``on_cache_write``, and
    ``on_cache_invalidate``, not by calling this type directly from ``BaseAction``.

    All mutating operations are serialized with a single :class:`asyncio.Lock`.
    There is **no** TTL and **no** single-flight in v1.
    """

    def __init__(self, max_size: int | None = None) -> None:
        """Create an empty store; ``max_size`` caps entries and enables eviction when full."""
        self._store: dict[str, CacheEntry] = {}
        self._tag_to_keys: defaultdict[CacheTag, set[str]] = defaultdict(set)
        self._key_to_tags: dict[str, set[CacheTag]] = {}
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

    @staticmethod
    def _tag_matches(stored: CacheTag, directive: CacheTag) -> bool:
        """Return True if ``directive`` matches ``stored`` (None in directive = wildcard)."""
        type_ok = directive.type is None or directive.type is stored.type
        key_ok = directive.key is None or directive.key == stored.key
        return type_ok and key_ok

    def _unindex_key(self, internal_key: str) -> None:
        """Remove ``internal_key`` from both directions of the tag index."""
        for tag in self._key_to_tags.pop(internal_key, set()):
            self._tag_to_keys[tag].discard(internal_key)
            if not self._tag_to_keys[tag]:
                del self._tag_to_keys[tag]

    def _evict_one(self) -> None:
        """Remove the entry with the smallest ``pipeline_duration_ms`` (capacity policy)."""
        if not self._store:
            return
        evict_key = min(self._store, key=lambda k: self._store[k].pipeline_duration_ms)
        del self._store[evict_key]
        self._unindex_key(evict_key)

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
        tags: list[CacheTag] | None = None,
    ) -> None:
        """Upsert ``result`` under the namespaced key and index ``tags``; evict one row if at ``max_size``."""
        internal_key = self._make_key(action_cls, user_key)
        async with self._lock:
            if self._max_size is not None and len(self._store) >= self._max_size:
                if internal_key not in self._store:
                    self._evict_one()
            self._unindex_key(internal_key)
            self._store[internal_key] = CacheEntry(
                result=result,
                pipeline_duration_ms=pipeline_duration_ms,
            )
            if tags:
                self._key_to_tags[internal_key] = set(tags)
                for tag in tags:
                    self._tag_to_keys[tag].add(internal_key)

    async def invalidate(self, action_cls: type, user_key: str) -> bool:
        """Delete one namespaced key and clean its tag index; return whether a row was removed."""
        internal_key = self._make_key(action_cls, user_key)
        async with self._lock:
            if internal_key in self._store:
                del self._store[internal_key]
                self._unindex_key(internal_key)
                return True
            return False

    async def evict_by_tags(self, directive_tags: frozenset[CacheTag]) -> int:
        """Evict all cached entries whose stored tags match any directive tag (wildcard-aware).

        A stored tag matches a directive tag when all non-None fields of the directive
        equal the corresponding fields of the stored tag."""
        async with self._lock:
            candidates: set[str] = set()
            for stored_tag, keys in list(self._tag_to_keys.items()):
                for directive_tag in directive_tags:
                    if self._tag_matches(stored_tag, directive_tag):
                        candidates.update(keys)
                        break
            for internal_key in candidates:
                del self._store[internal_key]
                self._unindex_key(internal_key)
            return len(candidates)

    async def clear(self, action_cls: type | None = None) -> int:
        """Drop all rows, or only rows for ``action_cls``; return how many were removed."""
        async with self._lock:
            if action_cls is None:
                count = len(self._store)
                self._store.clear()
                self._tag_to_keys.clear()
                self._key_to_tags.clear()
                return count
            prefix = self._class_prefix(action_cls)
            keys_to_remove = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._store[k]
                self._unindex_key(k)
            return len(keys_to_remove)
