# src/action_machine/intents/aspects/summary_aspect_decorator.py
"""
Decorator ``@summary_aspect`` declares the final action step.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Marks an action method as the final pipeline step. A summary aspect runs after
all regular aspects, consumes accumulated state, and returns a typed Result.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The decorator writes ``_new_aspect_meta`` on the method. The inspector reads it
into aspect snapshot entries, then ``ActionProductMachine`` executes the summary
method through ``_call_aspect``.

If ``@context_requires`` is present, ``ContextView`` is passed as ``ctx``:
- without context: ``(self, params, state, box, connections)``
- with context: ``(self, params, state, box, connections, ctx)``

    @summary_aspect(...)
           |
           v
    declaration invariants
           |
           v
    _new_aspect_meta on method
           |
           v
    inspector snapshot
           |
           v
    runtime final-step execution

"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from action_machine.model.exceptions import NamingSuffixError

# Parameter count without @context_requires.
_BASE_PARAM_COUNT = 5

# Parameter count with @context_requires.
_CTX_PARAM_COUNT = 6

# Parameter names used in validation messages.
_BASE_PARAM_NAMES = "self, params, state, box, connections"
_CTX_PARAM_NAMES = "self, params, state, box, connections, ctx"

# Required method suffix for summary aspect declarations.
_REQUIRED_SUFFIX = "_summary"

# Allowed bare method name that does not require suffix duplication.
_BARE_NAME = "summary"


def _description_type_invariant(description: Any) -> None:
    if not isinstance(description, str):
        raise TypeError(
            f"@summary_aspect expects a string description, "
            f"got {type(description).__name__}."
        )


def _description_non_empty_invariant(description: str) -> None:
    if not description.strip():
        raise ValueError(
            "@summary_aspect: description cannot be empty or whitespace. "
            "Provide a non-empty description for the final step."
        )


def _method_callable_invariant(func: Any) -> None:
    if not callable(func):
        raise TypeError(
            f"@summary_aspect can only be applied to methods. "
            f"Got object of type {type(func).__name__}: {func!r}."
        )


def _method_async_invariant(func: Any, description: str) -> None:
    if not asyncio.iscoroutinefunction(func):
        raise TypeError(
            f"@summary_aspect(\"{description}\"): method {func.__name__} "
            f"must be async (async def). "
            f"Synchronous methods are not supported."
        )


def _method_params_count_invariant(func: Any, description: str) -> None:
    has_context = hasattr(func, "_required_context_keys")
    expected_count = _CTX_PARAM_COUNT if has_context else _BASE_PARAM_COUNT
    expected_names = _CTX_PARAM_NAMES if has_context else _BASE_PARAM_NAMES
    sig = inspect.signature(func)
    param_count = len(sig.parameters)
    if param_count != expected_count:
        raise TypeError(
            f"@summary_aspect(\"{description}\"): method {func.__name__} "
            f"must accept {expected_count} parameters "
            f"({expected_names}), got {param_count}."
        )


def _method_suffix_invariant(func: Any, description: str) -> None:
    if func.__name__ != _BARE_NAME and not func.__name__.endswith(_REQUIRED_SUFFIX):
        raise NamingSuffixError(
            f"@summary_aspect(\"{description}\"): method '{func.__name__}' "
            f"must end with '{_REQUIRED_SUFFIX}'. "
            f"Rename it to '{func.__name__}{_REQUIRED_SUFFIX}' "
            f"or another name with the '{_REQUIRED_SUFFIX}' suffix."
        )


def summary_aspect(description: str) -> Callable[[Any], Any]:
    """
    Mark an action method as the final pipeline step.
    """
    _description_type_invariant(description)
    _description_non_empty_invariant(description)

    def decorator(func: Any) -> Any:
        """Validate target method and attach summary-aspect metadata."""
        _method_callable_invariant(func)
        _method_async_invariant(func, description)
        _method_params_count_invariant(func, description)
        _method_suffix_invariant(func, description)
        func._new_aspect_meta = {
            "type": "summary",
            "description": description,
        }
        return func

    return decorator
