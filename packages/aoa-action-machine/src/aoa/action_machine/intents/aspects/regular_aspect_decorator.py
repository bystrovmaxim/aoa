# packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/regular_aspect_decorator.py
"""
Decorator ``@regular_aspect`` declares a regular pipeline step.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Marks an action method as a regular aspect. The method must return a ``dict``
of fields that are merged into state.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The decorator writes ``_new_aspect_meta`` on the method. The inspector reads
that metadata into aspect snapshot entries. At runtime, the machine executes
regular aspects in declaration order and merges returned fields into state.

If ``@context_requires`` is present, ``ContextView`` is passed as ``ctx``:
- without context: ``(self, params, state, box, connections)``
- with context: ``(self, params, state, box, connections, ctx)``

    @regular_aspect(...)
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
    runtime state merge

"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError

# Parameter count without @context_requires.
_BASE_PARAM_COUNT = 5

# Parameter count with @context_requires.
_CTX_PARAM_COUNT = 6

# Parameter names used in validation messages.
_BASE_PARAM_NAMES = "self, params, state, box, connections"
_CTX_PARAM_NAMES = "self, params, state, box, connections, ctx"

# Required method suffix for regular aspect declarations.
_REQUIRED_SUFFIX = "_aspect"


def _description_type_invariant(description: Any) -> None:
    if not isinstance(description, str):
        raise TypeError(
            f"@regular_aspect expects a string description, "
            f"got {type(description).__name__}."
        )


def _description_non_empty_invariant(description: str) -> None:
    if not description.strip():
        raise ValueError(
            "@regular_aspect: description cannot be empty or whitespace. "
            "Provide a non-empty step description."
        )


def _method_callable_invariant(func: Any) -> None:
    if not callable(func):
        raise TypeError(
            f"@regular_aspect can only be applied to methods. "
            f"Got object of type {type(func).__name__}: {func!r}."
        )


def _method_async_invariant(func: Any, description: str) -> None:
    if not asyncio.iscoroutinefunction(func):
        raise TypeError(
            f"@regular_aspect(\"{description}\"): method {func.__name__} "
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
            f"@regular_aspect(\"{description}\"): method {func.__name__} "
            f"must accept {expected_count} parameters "
            f"({expected_names}), got {param_count}."
        )


def _method_suffix_invariant(func: Any, description: str) -> None:
    if not func.__name__.endswith(_REQUIRED_SUFFIX):
        raise NamingSuffixError(
            f"@regular_aspect(\"{description}\"): method '{func.__name__}' "
            f"must end with '{_REQUIRED_SUFFIX}'. "
            f"Rename to '{func.__name__}{_REQUIRED_SUFFIX}' "
            f"or another name with the '{_REQUIRED_SUFFIX}' suffix."
        )


def regular_aspect(description: str) -> Callable[[Any], Any]:
    """
    Mark an action method as a regular pipeline step.
    """
    _description_type_invariant(description)
    _description_non_empty_invariant(description)

    def decorator(func: Any) -> Any:
        """Validate target method and attach regular-aspect metadata."""
        _method_callable_invariant(func)
        _method_async_invariant(func, description)
        _method_params_count_invariant(func, description)
        _method_suffix_invariant(func, description)
        func._new_aspect_meta = {
            "type": "regular",
            "description": description,
        }
        return func

    return decorator
