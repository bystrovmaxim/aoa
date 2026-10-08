# packages/aoa-action-machine/src/aoa/action_machine/intents/access_decide/access_decide_decorator.py
"""
@access_decide — declare an operation's own answer about the object it is called on.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The object check is declared, not inherited. A class that needs one writes a
method whose name carries the required suffix and marks it with this decorator;
a class that needs none writes nothing, and then it simply has no object check.

What the declaration buys, compared with an inherited method:

- the check is **visible in the assembled graph**, like every other declaration;
- it is **at most one** per operation — two declarations are a declaration
  error, because two answers to the same question leave nobody able to say which
  one decided;
- it is **never inherited**: a subclass does not silently take over the decision
  its parent made about a different object;
- the step publishes **its own before and after events**, the way the other
  declared behaviours do.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @meta(...)                        ─┐
    @check_roles(...)                  │ declarations of the operation
    class CancelOrderAction(BaseAction[…]):
        @access_decide                ─┘  ◀── this module marks the method
        async def cancel_order_access_decide(self, params, context, box, connections) -> Verdict:
            …

    decoration ──▶ suffix + async + arity checked here, ``_access_decide_meta`` written on the method
    assembly   ──▶ AccessDecideIntentResolver finds the marked method in the class's own namespace
    runtime    ──▶ the object step calls it and turns its answer into a decision

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the method's name, its being ``async``, its arity, and the mark that says
"this method is the operation's object check".

OUT: what the check answers (the answer vocabulary), when it is called (the
cascade's order), and how a transport presents the result.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError

_ACCESS_DECIDE_SUFFIX = "_access_decide"
"""Required suffix for the declared object check's method name."""

_ACCESS_DECIDE_META_ATTR = "_access_decide_meta"
"""Attribute written on the method by ``@access_decide``."""

_CONTEXT_REQUIRES_ATTR = "_required_context_keys"
"""Attribute written by ``@context_requires``; adds the trailing ``ctx`` parameter."""

_EXPECTED_PARAMS_WITHOUT_CTX = 5
"""``self, params, context, box, connections``."""

_EXPECTED_PARAMS_WITH_CTX = 6
"""The same, plus the trailing ``ctx`` that ``@context_requires`` adds."""


def _method_suffix_invariant(func: Callable[..., Any]) -> None:
    if not func.__name__.endswith(_ACCESS_DECIDE_SUFFIX):
        raise NamingSuffixError(
            f"@access_decide: method '{func.__name__}' must end with '{_ACCESS_DECIDE_SUFFIX}'. "
            f"Rename it to '{func.__name__}{_ACCESS_DECIDE_SUFFIX}' "
            f"or another name with the '{_ACCESS_DECIDE_SUFFIX}' suffix."
        )


def _method_async_invariant(func: Callable[..., Any]) -> None:
    if not asyncio.iscoroutinefunction(func):
        raise TypeError(f"@access_decide: method '{func.__name__}' must be async (async def).")


def _method_params_count_invariant(func: Callable[..., Any]) -> None:
    has_context = hasattr(func, _CONTEXT_REQUIRES_ATTR)
    expected = _EXPECTED_PARAMS_WITH_CTX if has_context else _EXPECTED_PARAMS_WITHOUT_CTX
    actual = len(inspect.signature(func).parameters)
    if actual != expected:
        described = "self, params, context, box, connections" + (", ctx" if has_context else "")
        raise TypeError(
            f"@access_decide: method '{func.__name__}' must accept {expected} parameters "
            f"({described}), got {actual}."
            + (" Detected @context_requires, so the trailing ctx parameter is required." if has_context else "")
        )


def access_decide(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Mark a method as the operation's object check.

    Args:
        func: the method to declare, named with the ``_access_decide`` suffix.

    Returns:
        The same method, marked with ``_access_decide_meta``.

    Raises:
        NamingSuffixError: the method name does not carry the required suffix.
        TypeError: the method is not ``async``, or its arity is wrong.

    Example:
        @access_decide
        async def cancel_order_access_decide(self, params, context, box, connections):
            ...
    """
    _method_suffix_invariant(func)
    _method_async_invariant(func)
    _method_params_count_invariant(func)

    setattr(func, _ACCESS_DECIDE_META_ATTR, {"declared": True})

    return func
