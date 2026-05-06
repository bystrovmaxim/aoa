# src/action_machine/intents/on_error/on_error_intent_resolver.py
"""
OnErrorIntentResolver — resolves on-error handler callables from action classes.

``hydrate_error_handler_row`` rebuilds typed handler rows from immutable
``tuple[tuple[str, Any], ...]`` facet encodings emitted alongside decorators.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from action_machine.system_core.type_introspection import TypeIntrospection


@dataclass(frozen=True)
class OnErrorHandlerFacetHydration:
    """One handler decoded from facet ``node_meta`` (paired with ``@on_error`` on the owning class)."""

    method_name: str
    exception_types: tuple[type[Exception], ...]
    description: str
    method_ref: object
    context_keys: frozenset[str]


class OnErrorIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve on-error handler intent declarations from one action class.
    CONTRACT: Returns own-class ``@on_error`` callables in declaration order and does not materialize graph nodes.
    FAILURES: :exc:`ValueError` from :meth:`resolve_description` when ``_on_error_meta`` is missing or not a ``dict``.
    AI-CORE-END
    """

    @staticmethod
    def resolve_error_handlers(action_cls: type) -> list[Callable[..., Any]]:
        """Return own-class ``@on_error`` callables."""
        return TypeIntrospection.collect_own_class_callables(
            action_cls,
            lambda fn: getattr(fn, "_on_error_meta", None) is not None,
        )

    @staticmethod
    def resolve_description(call_like: Any) -> Any:
        """Return ``@on_error`` ``description`` from scratch; raise when ``_on_error_meta`` is not a ``dict``."""
        func = TypeIntrospection.unwrap_declaring_class_member(call_like)
        meta = getattr(func, "_on_error_meta", None)
        if not isinstance(meta, dict):
            raise ValueError(
                f"{TypeIntrospection.qualname_of(func)} has no usable @on_error description "
                "required for graph metadata resolution.",
            )
        return meta.get("description")

    @staticmethod
    def resolve_exception_types(call_like: Any) -> tuple[type[Exception], ...]:
        """Return ``@on_error`` exception types from callable scratch when present."""
        func = TypeIntrospection.unwrap_declaring_class_member(call_like)
        meta = getattr(func, "_on_error_meta", None)
        if not isinstance(meta, dict):
            return ()
        raw = meta.get("exception_types")
        if isinstance(raw, tuple) and all(isinstance(item, type) for item in raw):
            return raw
        return ()


def hydrate_error_handler_row(row: tuple[tuple[str, Any], ...]) -> OnErrorHandlerFacetHydration:
    """Rebuild :class:`OnErrorHandlerFacetHydration` from one facet ``node_meta`` row tuple."""

    d = dict(row)
    ck = d["context_keys"]
    if not isinstance(ck, frozenset):
        ck = frozenset(ck or ())
    et = d["exception_types"]
    exc_typed = cast("tuple[type[Exception], ...]", tuple(et))
    return OnErrorHandlerFacetHydration(
        method_name=d["method_name"],
        exception_types=exc_typed,
        description=d["description"],
        method_ref=d["method_ref"],
        context_keys=ck,
    )
