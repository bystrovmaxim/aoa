# packages/aoa-action-machine/src/aoa/action_machine/context/env_decorator.py
"""``@env`` — class decorator that registers lazy environment providers on a Context subclass."""

from collections.abc import Callable
from typing import Any, TypeVar

from aoa.action_machine.context.env_entry import EnvEntry

T = TypeVar("T")


def env(
    key: str,
    value: "Callable[[], T] | T",
    ttl: int = 0,
) -> Callable[[type], type]:
    """Register a lazy environment provider on a ``Context`` subclass.

    Stacks naturally: apply multiple ``@env`` decorators to the same class;
    each one adds its entry without overwriting the others.  Subclasses inherit
    parent entries and may add their own.

    Args:
        key: Logical name used to access the value via
             ``@context_requires("env.<key>")`` / ``Context.resolve("env.<key>")``.
        value: A zero-argument callable that returns the environment value, or a
               constant (automatically wrapped in ``lambda: value``).
        ttl: Cache lifetime in seconds.  ``0`` = cache forever (default);
             ``>0`` = re-call provider after ``ttl`` seconds; ``<0`` = ``ValueError``.

    Example::

        @env("feature_flag", lambda: read_flag("my-flag"), ttl=30)
        @env("region", "eu-west-1")          # constant — auto-wrapped
        @env("max_retries", 3)
        class AppContext(Context):
            ...
    """
    provider: Callable[[], Any] = value if callable(value) else lambda: value
    entry: EnvEntry[Any] = EnvEntry(key=key, provider=provider, ttl=ttl)

    def decorator(cls: type) -> type:
        # Inherit parent entries without mutating the parent dict.
        entries: dict[str, EnvEntry[Any]] = dict(getattr(cls, "__env_entries__", {}))
        entries[key] = entry
        cls.__env_entries__ = entries  # type: ignore[attr-defined]
        return cls

    return decorator
