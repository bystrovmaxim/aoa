# src/action_machine/core/action_generic_params.py
"""Resolve Params/Result types from ``BaseAction[P, R]`` subclasses (single place for generic extraction)."""

from __future__ import annotations

from typing import get_args, get_origin

from action_machine.core.base_action import BaseAction


def extract_action_params_result_types(action_cls: type) -> tuple[type | None, type | None]:
    """
    Walk ``action_cls`` MRO and ``__orig_bases__`` for a parameterized ``BaseAction[P, R]``.

    Returns concrete ``P`` and ``R`` types when both are classes; otherwise ``(None, None)``.
    """
    for klass in action_cls.__mro__:
        for base in getattr(klass, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is BaseAction:
                args = get_args(base)
                if len(args) >= 2:
                    p_type = args[0] if isinstance(args[0], type) else None
                    r_type = args[1] if isinstance(args[1], type) else None
                    return p_type, r_type
    return None, None
