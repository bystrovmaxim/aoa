# packages/aoa-action-machine/src/aoa/action_machine/runtime/cache_entry.py
"""
``CacheEntry`` — one materialized row returned by :meth:`CacheCoordinator.get_entry`.

The action's ``read_cache(params, entry)`` receives this object (and ``params``)
to validate or deserialize; it does **not** fetch the coordinator itself. The
machine is the only writer via ``put`` after ``on_cache_write`` returns ``True``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """
    Holds the cached pipeline ``result`` plus metadata for eviction and telemetry.

    ``read_cache`` may return ``None`` to signal a stale or incompatible row; the
    machine then invalidates the key and runs the aspect pipeline again.

    ``created_at`` and ``last_accessed_at`` use :func:`time.monotonic` for
    monotonic comparison, not wall-clock time.
    """

    result: Any
    pipeline_duration_ms: float
    created_at: float = field(default_factory=time.monotonic)
    last_accessed_at: float = field(default_factory=time.monotonic)
    access_count: int = 0
