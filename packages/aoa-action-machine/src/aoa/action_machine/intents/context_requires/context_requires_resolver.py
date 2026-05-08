# packages/aoa-action-machine/src/aoa/action_machine/intents/context_requires/context_requires_resolver.py
"""
ContextRequiresResolver — reads ``@context_requires`` keys from callables.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose declared dot-path keys for aspects, handlers, or compensators that use
``@context_requires``. The decorator stores ``frozenset[str]`` on the function
object as ``_required_context_keys``; this resolver returns a stable ``list``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    callable (possibly bound method)
            │
            ▼  unwrap ``__func__`` when present
    underlying function / callable
            │
            ▼  read ``_required_context_keys`` (frozenset from decorator)
            │
            ▼  sorted(...) → ``list[str]``

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ContextRequiresResolver:
    """
    AI-CORE-BEGIN
    ROLE: Normalize ``@context_requires`` scratch into an ordered key list from any callable reference.
    CONTRACT: Accepts bound/unbound methods and plain decorated callables; returns sorted keys or empty list.
    INVARIANTS: Reads only ``_required_context_keys`` frozensets set by ``context_requires``; ignores invalid types.
    AI-CORE-END
    """

    @staticmethod
    def resolve_required_context_keys(fn: Callable[..., Any]) -> list[str]:
        """
        Return declared context keys for ``fn``, sorted for stable ordering.

        Handles bound instance methods by following ``__func__`` to the
        decorated callable. When ``@context_requires`` was never applied,
        returns an empty list.
        """
        underlying = getattr(fn, "__func__", fn)
        raw = getattr(underlying, "_required_context_keys", None)
        if raw is None:
            return []
        if not isinstance(raw, frozenset):
            return []
        return sorted(raw)
