# src/action_machine/runtime/binding/action_generic_params.py
"""
Low-level helpers to resolve generic type arguments (``ForwardRef``, strings).

Primary extraction of ``P`` / ``R`` from ``BaseAction[P, R]`` lives in
:mod:`action_machine.runtime.binding.extract_action_params_result_types`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Shared resolution logic for ``typing`` generic arguments used when walking
action class MROs. Keeps **no** import of :class:`action_machine.model.base_action.BaseAction`
at module load so callers that only need ref resolution avoid pulling ``model``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``_resolve_forward_ref`` / ``_resolve_generic_arg`` are import-safe without ``BaseAction``.
- Only fully resolved runtime ``type`` objects are returned from helpers.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Generic-arg resolution helpers for runtime binding.
CONTRACT: Resolve single generic args to concrete types when possible.
INVARIANTS: Stdlib + action class namespace only; no ``model`` imports.
FLOW: ForwardRef/string/type -> optional concrete ``type``.
FAILURES: Swallow resolution errors; return ``None``.
EXTENSION POINTS: Alternate ``evaluate_forward_ref`` strategies.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
import typing
from typing import Any, ForwardRef

__all__ = ["_resolve_forward_ref", "_resolve_generic_arg"]


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
