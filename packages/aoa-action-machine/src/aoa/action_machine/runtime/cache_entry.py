# packages/aoa-action-machine/src/aoa/action_machine/runtime/cache_entry.py
"""
``StoredCacheEntry`` and ``CacheEntry`` — what a cache store keeps, and what ``@cache_read`` receives.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The store keeps bytes: the Result's JSON in UTF-8, written by the machine, with
the metadata it needs for eviction and telemetry. That is ``StoredCacheEntry``, the
row ``get_entry`` returns and ``put`` builds, so an in-memory store and Redis do the
same job. On a hit the machine reads the bytes into a new Result with the action's
Result type and hands ``@cache_read`` a ``CacheEntry``: that new Result and the
stored metadata. No caller ever receives the object another caller got.

``created_at`` and ``last_accessed_at`` use :func:`time.monotonic` for monotonic
comparison, not wall-clock time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StoredCacheEntry:
    """
    AI-CORE-BEGIN
    ROLE: One row of a cache store: the Result's JSON bytes plus metadata.
    CONTRACT: ``payload`` is ``result.model_dump_json()`` in UTF-8, written by the machine; a store never sees a Result.
    AI-CORE-END
    """

    payload: bytes
    pipeline_duration_ms: float
    created_at: float = field(default_factory=time.monotonic)
    last_accessed_at: float = field(default_factory=time.monotonic)
    access_count: int = 0


@dataclass
class CacheEntry:
    """
    What ``@cache_read`` receives on a hit: a Result read from the stored bytes, and the stored metadata.

    ``@cache_read`` may return ``None`` to signal a stale row; the machine then
    invalidates the key and runs the aspect pipeline again.
    """

    result: Any
    pipeline_duration_ms: float
    created_at: float = field(default_factory=time.monotonic)
    last_accessed_at: float = field(default_factory=time.monotonic)
    access_count: int = 0

    @classmethod
    def from_stored(cls, stored: StoredCacheEntry, result: Any) -> CacheEntry:
        """The entry ``@cache_read`` sees: ``result`` read from ``stored.payload``, with ``stored``'s metadata."""
        return cls(
            result=result,
            pipeline_duration_ms=stored.pipeline_duration_ms,
            created_at=stored.created_at,
            last_accessed_at=stored.last_accessed_at,
            access_count=stored.access_count,
        )
