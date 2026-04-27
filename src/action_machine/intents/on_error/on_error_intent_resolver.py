# src/action_machine/intents/on_error/on_error_intent_resolver.py
"""OnErrorIntentResolver — resolves on-error handler callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.introspection_tools.type_introspection import TypeIntrospection


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
