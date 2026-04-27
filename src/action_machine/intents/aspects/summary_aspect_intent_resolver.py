# src/action_machine/intents/aspects/summary_aspect_intent_resolver.py
"""SummaryAspectIntentResolver — resolves summary aspect callables from action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.introspection_tools.type_introspection import TypeIntrospection


class SummaryAspectIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve summary aspect intent declarations from one action class.
    CONTRACT: Returns own-class ``@summary_aspect`` callables in declaration order and does not materialize graph nodes.
    AI-CORE-END
    """

    @staticmethod
    def resolve_summary_aspects(action_cls: type) -> list[Callable[..., Any]]:
        """Return own-class ``@summary_aspect`` callables."""
        return TypeIntrospection.collect_own_class_callables(
            action_cls,
            lambda fn: (
                isinstance(meta := getattr(fn, "_new_aspect_meta", None), dict)
                and meta.get("type") == "summary"
            ),
        )
