# packages/aoa-action-machine/src/aoa/action_machine/context/env_entry.py
"""EnvEntry — lazy environment value with optional TTL cache."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast


@dataclass(frozen=True)
class EnvEntry[T]:
    """Lazy environment value stored on a Context subclass by the ``@env`` decorator.

    The provider is called on first access and its result cached according to
    ``ttl``.  ``_cache`` is mutable inside the frozen dataclass — the reference
    is frozen, the dict contents are not.

    Args:
        key: Logical name used to look up this entry via ``Context.resolve("env.<key>")``.
        provider: Zero-argument callable returning the environment value.
        ttl: Cache lifetime in seconds.  ``0`` = cache forever (default);
             ``>0`` = re-call provider after ``ttl`` seconds; ``<0`` = ``ValueError``.
    """

    key: str
    provider: Callable[[], T]
    ttl: int = 0
    _cache: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.ttl < 0:
            raise ValueError(
                f"EnvEntry '{self.key}': ttl must be >= 0, got {self.ttl}"
            )

    def get(self) -> T:
        """Return cached value or call the provider (respecting TTL)."""
        if "v" in self._cache:
            value, cached_at = self._cache["v"]
            if self.ttl == 0 or (time.monotonic() - cached_at) < self.ttl:
                return cast("T", value)
        value = self.provider()
        self._cache["v"] = (value, time.monotonic())
        return value
