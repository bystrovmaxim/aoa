# src/action_machine/legacy/deprecated.py
"""
deprecated — ``@deprecated`` decorator for runtime :class:`DeprecationWarning`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Wraps callables so each invocation emits a :class:`DeprecationWarning` with a fixed
message and correct stack attribution (call site, not the decorator internals).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    caller  →  wrapped(...)  →  warnings.warn(..., stacklevel=2)  →  original callable

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    @deprecated("old_fn is deprecated; use new_fn instead.")
    def old_fn() -> None: ...

Edge case: apply **above** ``@classmethod`` / ``@staticmethod`` if those decorators are used
(outermost ``@deprecated`` last in source order for methods — i.e. ``@deprecated`` then
``@classmethod`` is wrong; use ``@classmethod`` then ``@deprecated`` wrapping the descriptor).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Small decorator factory for consistent DeprecationWarning emission.
CONTRACT: Pass a stable message string; grep ``@deprecated`` or ``deprecated(`` to find call sites.
INVARIANTS: stacklevel fixed at 2 for plain functions and bound methods.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def deprecated(message: str) -> Callable[[F], F]:
    """
    AI-CORE-BEGIN
    ROLE: Mark a function or method deprecated at runtime.
    CONTRACT: Message is shown verbatim; warning category DeprecationWarning.
    AI-CORE-END
    """

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return fn(*args, **kwargs)

        return cast(F, wrapper)

    return decorator
