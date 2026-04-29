# src/action_machine/intents/compensate/compensate_intent_resolver.py
"""CompensateIntentResolver — resolves compensator callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.system_core.type_introspection import TypeIntrospection
from graph.base_intent_inspector import BaseIntentInspector


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

    @staticmethod
    def resolve_description(call_like: Any) -> str | None:
        """Return ``@compensate`` description from callable scratch when present."""
        func = BaseIntentInspector._unwrap_declaring_class_member(call_like)
        return TypeIntrospection.description_from_meta(getattr(func, "_compensate_meta", None))

    @staticmethod
    def resolve_target_aspect_name(call_like: Any) -> str | None:
        """Return ``@compensate`` target_aspect_name from callable scratch when present."""
        func = BaseIntentInspector._unwrap_declaring_class_member(call_like)
        return TypeIntrospection.target_aspect_name_from_meta(getattr(func, "_compensate_meta", None))
