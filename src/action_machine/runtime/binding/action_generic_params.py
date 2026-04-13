# src/action_machine/runtime/binding/action_generic_params.py
"""
Resolve ``Params``/``Result`` runtime types from ``BaseAction[P, R]`` declarations.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module centralizes generic type extraction for runtime binding.
Given an action class, it resolves declared ``P`` and ``R`` from
``BaseAction[P, R]`` including nested inheritance and forward references.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Resolution scans ``__mro__`` and ``__orig_bases__`` in deterministic order.
- Only fully resolved runtime ``type`` objects are returned.
- If no valid parameterized ``BaseAction[P, R]`` is found, returns ``(None, None)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    action class
        |
        v
    walk MRO -> inspect __orig_bases__
        |
        v
    find BaseAction[P, R] generic origin
        |
        v
    resolve args (type / ForwardRef / string)
        |
        v
    return (P_type, R_type) or (None, None)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    ``class A(BaseAction[MyParams, MyResult])`` resolves directly to
    ``(MyParams, MyResult)``.

Edge case:
    Forward references like ``BaseAction["Params", "Result"]`` are resolved
    through module/global namespace; unresolved refs yield ``None``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Forward-ref resolution relies on module symbols being available at runtime.
- Non-type generic arguments are ignored as unresolved.
- Private typing internals may vary by Python version; fallback paths are used.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Runtime generic resolver for BaseAction parameter/result contracts.
CONTRACT: Return concrete P/R types when resolvable; otherwise return None tuple.
INVARIANTS: MRO search + generic origin check + type-only outputs.
FLOW: locate BaseAction generic -> resolve refs -> return pair to runtime validators.
FAILURES: Unresolvable refs or malformed generics degrade to (None, None).
EXTENSION POINTS: Add richer ref-resolution strategies for advanced typing cases.
AI-CORE-END
"""

from __future__ import annotations

import sys
import typing
from typing import Any, ForwardRef, get_args, get_origin

from action_machine.model.base_action import BaseAction


def _resolve_forward_ref(ref: ForwardRef, action_class: type) -> type | None:
    """
    Resolve a ForwardRef using the action class module and namespace.

    Uses ``ForwardRef._evaluate`` when public ``typing.evaluate_forward_ref``
    is unavailable.
    """
    module = sys.modules.get(action_class.__module__, None)
    globalns: dict[str, Any] = vars(module) if module else {}
    localns: dict[str, Any] = {action_class.__name__: action_class}
    guard: frozenset[Any] = frozenset()

    try:
        evaluate_forward_ref = getattr(typing, "evaluate_forward_ref", None)
        if evaluate_forward_ref is not None:
            resolved = evaluate_forward_ref(
                ref,
                globals=globalns,
                locals=localns,
                type_params=(),
            )
        else:
            resolved = ref._evaluate(
                globalns, localns, None, recursive_guard=guard
            )

        if isinstance(resolved, type):
            return resolved
    except Exception:
        pass
    return None


def _resolve_generic_arg(arg: Any, action_class: type) -> type | None:
    """Resolve a single generic argument (type, ForwardRef, or string)."""
    if isinstance(arg, type):
        return arg
    if isinstance(arg, ForwardRef):
        return _resolve_forward_ref(arg, action_class)
    if isinstance(arg, str):
        return _resolve_forward_ref(ForwardRef(arg), action_class)
    return None


def extract_action_params_result_types(action_cls: type) -> tuple[type | None, type | None]:
    """
    Walk ``action_cls`` MRO and ``__orig_bases__`` for a parameterized ``BaseAction[P, R]``.

    Resolves string / ForwardRef parameters (e.g. nested ``Params`` / ``Result``).

    Returns ``(P, R)`` when both resolve to types; otherwise continues searching,
    then ``(None, None)`` if nothing matches.
    """
    for klass in action_cls.__mro__:
        for base in getattr(klass, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is BaseAction:
                args = get_args(base)
                if len(args) >= 2:
                    p_type = _resolve_generic_arg(args[0], action_cls)
                    r_type = _resolve_generic_arg(args[1], action_cls)
                    if p_type is not None and r_type is not None:
                        return p_type, r_type
    return None, None
