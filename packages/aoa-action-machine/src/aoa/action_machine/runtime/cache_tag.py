# packages/aoa-action-machine/src/aoa/action_machine/runtime/cache_tag.py
"""CacheTag — typed tag for cache entry indexing and invalidation matching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CacheTag:
    """One tag attached to a cache entry or used as a matching directive during invalidation.

    Specify ``type``, ``key``, or both:

    ``CacheTag(type=Order, key=42)``
        Exact tag — indexes or matches only entries for Order entity with id 42.

    ``CacheTag(type=Order)``
        Type wildcard — during invalidation matches all entries carrying any
        ``CacheTag`` with ``type=Order``, regardless of key.

    ``CacheTag(key=42)``
        Key wildcard — during invalidation matches all entries carrying any
        ``CacheTag`` with ``key=42``, regardless of type.

    At least one of ``type`` or ``key`` must be provided.

    AI-CORE-BEGIN
    ROLE: Immutable value object representing one dimension of a cache entry's identity — used both when indexing an entry on write and as a matching directive during tag-based invalidation.
    CONTRACT: At least one of type/key must be non-None; frozen and hashable so it can be used as a dict key and in frozensets.
    INVARIANTS: Wildcard semantics apply only during invalidation matching — stored tags are always explicit (at least one non-None field); CacheTag(type=T) matches stored CacheTag(type=T, key=K) during eviction.
    AI-CORE-END
    """

    type: type[Any] | None = None
    key: str | int | None = None

    def __post_init__(self) -> None:
        """Reject tags with no identifying information."""
        if self.type is None and self.key is None:
            raise ValueError("CacheTag requires at least one of: type, key.")
