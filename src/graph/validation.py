# src/graph/validation.py
"""
Small **invariant checks** for interchange graph models (:class:`~graph.base_graph_edge.BaseGraphEdge`,
:class:`~graph.base_graph_node.BaseGraphNode`).

These are public helpers so constructors stay thin and rules stay in one place.

═══════════════════════════════════════════════════════════════════════════════
RELATED MODULES
═══════════════════════════════════════════════════════════════════════════════

- :class:`action_machine.tools.type_introspection.TypeIntrospection` — stable type ids use :meth:`~action_machine.tools.type_introspection.TypeIntrospection.full_qualname`,
  not how arbitrary caller strings are validated.
- This module — how **caller-supplied** strings and references are *validated* before freezing a model.
"""

from __future__ import annotations


def require_non_empty_str(field: str, value: object) -> str:
    """
    Require a non-whitespace string (after strip).

    Returns the original string (not stripped) when valid.
    """
    if not isinstance(value, str):
        msg = f"{field} must be str, not {type(value).__name__}"
        raise TypeError(msg)
    if value.strip() == "":
        msg = f"{field} must be a non-empty string (got empty or whitespace-only)"
        raise ValueError(msg)
    return value


def require_non_null[T](field: str, value: T | None) -> T:
    """Require a reference that is not ``None``."""
    if value is None:
        msg = f"{field} must not be None"
        raise ValueError(msg)
    return value
