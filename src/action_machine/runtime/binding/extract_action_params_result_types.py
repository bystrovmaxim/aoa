# src/action_machine/runtime/binding/extract_action_params_result_types.py
"""
Extract concrete ``P`` / ``R`` runtime types from ``BaseAction[P, R]`` on ``action_cls``.

Walks ``__mro__`` and ``__orig_bases__``; resolves generic arguments via
:func:`action_machine.runtime.binding.action_generic_params._resolve_generic_arg`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import get_args, get_origin

from action_machine.runtime.binding.action_generic_params import _resolve_generic_arg


@lru_cache(maxsize=1)
def _base_action_type() -> type:
    """Late import: ``base_action`` may still be initializing when this module loads."""
    # pylint: disable=import-outside-toplevel
    from action_machine.model.base_action import BaseAction

    return BaseAction


def extract_action_params_result_types(action_cls: type) -> tuple[type | None, type | None]:
    """
    Walk ``action_cls`` MRO and ``__orig_bases__`` for a parameterized ``BaseAction[P, R]``.

    Resolves string / ForwardRef parameters (e.g. nested ``Params`` / ``Result``).

    Returns ``(P, R)`` when both resolve to types; otherwise continues searching,
    then ``(None, None)`` if nothing matches.
    """
    base_action = _base_action_type()
    for klass in action_cls.__mro__:
        for base in getattr(klass, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is base_action:
                args = get_args(base)
                if len(args) >= 2:
                    p_type = _resolve_generic_arg(args[0], action_cls)
                    r_type = _resolve_generic_arg(args[1], action_cls)
                    if p_type is not None and r_type is not None:
                        return p_type, r_type
    return None, None
