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
