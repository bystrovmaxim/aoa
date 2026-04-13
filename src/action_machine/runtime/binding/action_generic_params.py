# src/action_machine/runtime/binding/action_generic_params.py
"""Resolve Params/Result types from ``BaseAction[P, R]`` subclasses (single place for generic extraction)."""

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
