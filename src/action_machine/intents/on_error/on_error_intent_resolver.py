# src/action_machine/intents/on_error/on_error_intent_resolver.py
"""OnErrorIntentResolver — resolves on-error handler callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.system_core.type_introspection import TypeIntrospection
from graph.base_intent_inspector import BaseIntentInspector


class OnErrorIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve on-error handler intent declarations from one action class.
    CONTRACT: Returns own-class ``@on_error`` callables in declaration order and does not materialize graph nodes.
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
    def resolve_description(call_like: Any) -> str | None:
        """Return ``@on_error`` description from callable scratch when present."""
        func = BaseIntentInspector._unwrap_declaring_class_member(call_like)
        return TypeIntrospection.description_from_meta(getattr(func, "_on_error_meta", None))

    @staticmethod
    def resolve_exception_types(call_like: Any) -> tuple[type[Exception], ...]:
        """Return ``@on_error`` exception types from callable scratch when present."""
        func = BaseIntentInspector._unwrap_declaring_class_member(call_like)
        meta = getattr(func, "_on_error_meta", None)
        if not isinstance(meta, dict):
            return ()
        raw = meta.get("exception_types")
        if isinstance(raw, tuple) and all(isinstance(item, type) for item in raw):
            return raw
        return ()
