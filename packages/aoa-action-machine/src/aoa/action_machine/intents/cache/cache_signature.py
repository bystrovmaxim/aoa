# packages/aoa-action-machine/src/aoa/action_machine/intents/cache/cache_signature.py
"""
The signature each cache declaration must declare — names, order and types, checked as invariants.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The machine calls a cache declaration positionally, so its signature is part of the
contract. Every kind starts as the other declarations do, ``self, params, box,
connections``, then takes what only it has, then ``ctx`` when ``@context_requires``
sits under it:

    @cache_key          self, params, box, connections                    -> str | None
    @cache_read         self, params, box, connections, entry             -> Result | None
    @cache_write        self, params, box, connections, result, duration_ms -> list[CacheTag] | None
    @cache_invalidate   self, params, box, connections, result            -> list[CacheTag] | None
    @cache_entity_key   self, params, box, connections, entity            -> str

Names, order and the presence of annotations are checked here, when the class body
runs. The types those annotations name are checked when the graph is assembled
(``cache_signature_types``), because ``params`` is annotated with the operation's own
``Params``, which does not exist yet while its class body runs. Both refuse with
``AspectSignatureError``.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, Literal

from aoa.action_machine.exceptions.aspect_signature_error import AspectSignatureError

CacheKind = Literal["key", "read", "write", "invalidate", "entity_key"]

_COMMON = ("self", "params", "box", "connections")
_OWN: dict[str, tuple[str, ...]] = {
    "key": (),
    "read": ("entry",),
    "write": ("result", "duration_ms"),
    "invalidate": ("result",),
    "entity_key": ("entity",),
}
RETURNS = {
    "key": "str | None",
    "read": "the operation's Result | None",
    "write": "list[CacheTag] | None",
    "invalidate": "list[CacheTag] | None",
    "entity_key": "str",
}


def decorator_name(kind: str) -> str:
    """``@cache_<kind>``, as the developer writes it."""
    return f"@cache_{kind}"


def expected_names(kind: str, func: Callable[..., Any]) -> tuple[str, ...]:
    """The parameter names this declaration must use, in order, given ``@context_requires``."""
    names = (*_COMMON, *_OWN[kind])
    return (*names, "ctx") if hasattr(func, "_required_context_keys") else names


def handed_over(kind: str) -> str:
    """What the machine hands this kind, for messages."""
    return f"the machine hands over ({', '.join((*_COMMON, *_OWN[kind]))}) in that order"


def validate_names(kind: str, func: Callable[..., Any]) -> None:
    """Refuse a signature whose parameters are renamed, reordered, missing or extra."""
    expected = expected_names(kind, func)
    actual = tuple(inspect.signature(func).parameters)
    if actual == expected:
        return
    hint = ""
    if actual and actual[-1] == "ctx" and not hasattr(func, "_required_context_keys"):
        hint = f" This declaration takes ctx but asks for no context: put @context_requires(...) under {decorator_name(kind)}."
    elif hasattr(func, "_required_context_keys") and (not actual or actual[-1] != "ctx"):
        hint = " This declaration asked for context, so it must take the trailing ctx parameter."
    raise AspectSignatureError(
        f"{decorator_name(kind)}: method '{func.__name__}' must declare its parameters as "
        f"({', '.join(expected)}), got ({', '.join(actual)}). {handed_over(kind).capitalize()}, and Python "
        f"binds by position. Refused while the class body was executing.{hint}"
    )


def validate_annotated(kind: str, func: Callable[..., Any]) -> None:
    """Refuse a parameter other than ``self`` without an annotation, or a missing return annotation."""
    signature = inspect.signature(func)
    unannotated = [
        name
        for name, parameter in signature.parameters.items()
        if name != "self" and parameter.annotation is inspect.Parameter.empty
    ]
    if unannotated:
        raise AspectSignatureError(
            f"{decorator_name(kind)}: method '{func.__name__}' must annotate every parameter it receives; "
            f"({', '.join(unannotated)}) carry no annotation. Refused while the class body was executing."
        )
    if signature.return_annotation is inspect.Signature.empty:
        raise AspectSignatureError(
            f"{decorator_name(kind)}: method '{func.__name__}' must annotate what it returns ({RETURNS[kind]})."
        )


__all__ = ["RETURNS", "CacheKind", "decorator_name", "expected_names", "handed_over", "validate_annotated", "validate_names"]
