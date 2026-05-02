# src/action_machine/intents/compensate/compensate_decorator.py
"""
Compensate decorator module for declaring saga compensators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator ``@compensate(target_aspect_name, description)`` marks an async
action method as compensator for a target regular aspect. On pipeline failure,
compensators for already executed aspects are invoked in reverse order
(Saga rollback pattern).

The decorator validates declarations at class-definition time and writes
``_compensate_meta`` on the method for later inspector/builder collection.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @compensate(...)
          |
          v
    method._compensate_meta declaration
          |
          v
    ``CompensatorGraphEdge`` emission on ``ActionGraphNode``
          |
          v
    compensator facet snapshot
          |
          v
    runtime rollback invocation in reverse order

Binding uses target aspect *method name string* (``target_aspect_name``), not
direct callable references. This removes method-order coupling in class body.
Aspect existence/type validation is deferred to build stage when class surface
is fully assembled.

═══════════════════════════════════════════════════════════════════════════════
WRITTEN ATTRIBUTE
═══════════════════════════════════════════════════════════════════════════════

Decorator writes attribute on function:

    func._compensate_meta = {
        "target_aspect_name": target_aspect_name,
        "description": description,
    }

This attribute is read by compensator collectors (``CompensatorGraphEdge``
resolution on the action class) scanning ``vars(cls)`` to create compensator entries.

═══════════════════════════════════════════════════════════════════════════════
INTERACTION WITH @context_requires
═══════════════════════════════════════════════════════════════════════════════

Compensator may use ``@context_requires``. Decorator order:

    @context_requires("user.role", "tenant.id")
    @compensate("process_payment_aspect", "Rollback payment")
    async def rollback_payment_compensate(self, params, state_before,
                                           state_after, box, connections,
                                           error, ctx):
        ...

``@context_requires`` writes ``_required_context_keys`` onto function.
``@compensate`` checks this attribute and adjusts expected parameter count:
7 without ``ctx``, 8 with ``ctx``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.compensate import compensate

    class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

        @regular_aspect("Charge payment")
        async def process_payment_aspect(self, params, state, box, connections):
            ...

        @compensate("process_payment_aspect", "Rollback payment")
        async def rollback_payment_compensate(self, params, state_before,
                                               state_after, box, connections,
                                               error):
            ...
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_COMPENSATE_SUFFIX = "_compensate"
"""
Required suffix for compensator method names.
"""

_EXPECTED_PARAMS_WITHOUT_CTX = 7
"""
Expected compensator parameter count without @context_requires.
"""

_EXPECTED_PARAMS_WITH_CTX = 8
"""
Expected compensator parameter count with @context_requires.
"""

_COMPENSATE_META_ATTR = "_compensate_meta"
"""
Attribute name written by @compensate decorator.
"""

_CONTEXT_REQUIRES_ATTR = "_required_context_keys"
"""
Attribute name written by @context_requires decorator.
"""


def _target_aspect_type_invariant(target_aspect_name: Any) -> None:
    if not isinstance(target_aspect_name, str):
        raise TypeError(
            f"@compensate: target_aspect_name must be a string, "
            f"got {type(target_aspect_name).__name__}"
        )


def _target_aspect_non_empty_invariant(target_aspect_name: str) -> None:
    if not target_aspect_name.strip():
        raise ValueError(
            "@compensate: target_aspect_name cannot be empty"
        )


def _description_type_invariant(description: Any) -> None:
    if not isinstance(description, str):
        raise TypeError(
            f"@compensate: description must be a string, "
            f"got {type(description).__name__}"
        )


def _description_non_empty_invariant(description: str) -> None:
    if not description.strip():
        raise ValueError(
            "@compensate: description cannot be empty"
        )


def _method_suffix_invariant(method_name: str) -> None:
    if not method_name.endswith(_COMPENSATE_SUFFIX):
        raise ValueError(
            f"@compensate: method name '{method_name}' must end with "
            f"'{_COMPENSATE_SUFFIX}'."
        )


def _method_async_invariant(func: Callable[..., Any], method_name: str) -> None:
    if not asyncio.iscoroutinefunction(func):
        raise TypeError(
            f"@compensate: method '{method_name}' must be async (async def)."
        )


def _method_params_count_invariant(func: Callable[..., Any], method_name: str) -> None:
    has_context = hasattr(func, _CONTEXT_REQUIRES_ATTR)
    expected_params = (
        _EXPECTED_PARAMS_WITH_CTX if has_context
        else _EXPECTED_PARAMS_WITHOUT_CTX
    )
    sig = inspect.signature(func)
    actual_params = len(sig.parameters)
    if actual_params != expected_params:
        if has_context:
            params_desc = (
                "self, params, state_before, state_after, "
                "box, connections, error, ctx"
            )
        else:
            params_desc = (
                "self, params, state_before, state_after, "
                "box, connections, error"
            )

        raise TypeError(
            f"@compensate: method '{method_name}' must accept "
            f"{expected_params} parameters ({params_desc}), "
            f"got {actual_params}. "
            f"{'Detected @context_requires, so ctx parameter is required.' if has_context else ''}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Decorator @compensate
# ─────────────────────────────────────────────────────────────────────────────


def compensate(
    target_aspect_name: str,
    description: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Declare a compensator method for a target regular aspect.

    Args:
        target_aspect_name:
            Name of target regular-aspect method (for example,
            ``"process_payment_aspect"``). Must be non-empty. Existence/type
            validation is performed at build stage, not here.

        description:
            Human-readable compensator description used in plugin events,
            logging, and graph metadata.

    Returns:
        Decorator that writes ``_compensate_meta`` on method and returns it.

    Raises:
        TypeError:
            - target_aspect_name is not a string.
            - description is not a string.
            - method is not async.
            - invalid parameter arity.
        ValueError:
            - target_aspect_name is empty.
            - description is empty.
            - method name does not end with ``"_compensate"``.

    Example:
        @compensate("process_payment_aspect", "Rollback payment")
        async def rollback_payment_compensate(self, params, state_before,
                                               state_after, box,
                                               connections, error):
            ...
    """

    # ── Decorator argument validation ────────────────────────────────────────

    _target_aspect_type_invariant(target_aspect_name)
    _target_aspect_non_empty_invariant(target_aspect_name)
    _description_type_invariant(description)
    _description_non_empty_invariant(description)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Validate decorated method and write ``_compensate_meta``.
        """

        method_name = func.__name__

        # ── Method suffix validation ───────────────────────────────────────

        _method_suffix_invariant(method_name)

        # ── Async declaration validation ───────────────────────────────────

        _method_async_invariant(func, method_name)

        # ── Parameter arity validation ─────────────────────────────────────

        _method_params_count_invariant(func, method_name)

        # ── Write method metadata ──────────────────────────────────────────

        setattr(func, _COMPENSATE_META_ATTR, {
            "target_aspect_name": target_aspect_name.strip(),
            "description": description.strip(),
        })

        return func

    return decorator
