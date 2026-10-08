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
        @access_decide("Check the order belongs to the caller")
        @context_requires("user.user_id")                         ─┘  ◀── this module marks it
        async def cancel_order_access_decide(
            self,
            params: CancelOrderAction.Params,
            box: ToolsBox,
            connections: dict[str, BaseResource],
            ctx: ContextView,
        ) -> Verdict:
            …

    decoration ──▶ description + suffix + async + names in order + annotations checked here,
                   ``_access_decide_meta`` written on the method
    assembly   ──▶ AccessDecideIntentResolver finds the marked method in the class's own namespace,
                   and the annotations are resolved and checked against the contract types
    runtime    ──▶ the object step calls it and turns its answer into a decision

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the description, the method's name, its being ``async``, the names and order of its
parameters, its annotations, and the mark that says "this method is the operation's object
check". The types those annotations name are checked at assembly, where they resolve.

OUT: what the check answers (the answer vocabulary), when it is called (the
cascade's order), and how a transport presents the result.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.intents.access_decide.access_decide_signature import (
    validate_annotated,
    validate_names,
)

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


def _method_callable_invariant(func: Any) -> None:
    if not callable(func):
        raise TypeError(
            f"@access_decide can only be applied to methods. Got object of type {type(func).__name__}: {func!r}."
        )


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


def access_decide(description: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Mark a method as the operation's object check, and say what it checks.

    Args:
        description: What the check decides, in the developer's words.

    Returns:
        A decorator that marks the method with ``_access_decide_meta`` — its description
        included — and returns it unchanged.

    Raises:
        TypeError: the description is not a string, the decorator is applied to something
            that is not a method, the method is not ``async``, or its signature does not
            follow the contract.
        ValueError: the description is empty or whitespace.
        NamingSuffixError: the method name does not carry the required suffix.

    Example:
        @access_decide("Check the order belongs to the caller")
        async def cancel_order_access_decide(
            self,
            params: CancelOrderAction.Params,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> Verdict:
            ...
    """
    if not isinstance(description, str):
        raise TypeError(
            f"@access_decide expects a string description, got {type(description).__name__}."
        )
    if not description.strip():
        raise ValueError(
            "@access_decide: description cannot be empty or whitespace. "
            "Say what the check decides."
        )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _method_callable_invariant(func)
        _method_suffix_invariant(func)
        _method_async_invariant(func)
        validate_names(func)
        validate_annotated(func)

        setattr(func, _ACCESS_DECIDE_META_ATTR, {"declared": True, "description": description})

        return func

    return decorator
