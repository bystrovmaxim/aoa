# src/action_machine/intents/compensate/compensate_intent_resolver.py
"""CompensateIntentResolver — resolves compensator callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.introspection_tools.type_introspection import TypeIntrospection


class CompensateIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve compensator intent declarations from one action class.
    CONTRACT: Returns own-class ``@compensate`` callables in declaration order and does not materialize graph nodes.
    AI-CORE-END
    """

    @staticmethod
    def resolve_compensators(action_cls: type) -> list[Callable[..., Any]]:
        """Return own-class ``@compensate`` callables."""
        return TypeIntrospection.collect_own_class_callables(
            action_cls,
            lambda fn: getattr(fn, "_compensate_meta", None) is not None,
        )
